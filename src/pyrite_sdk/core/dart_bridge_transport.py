from __future__ import annotations

import asyncio
import contextlib
import os
import threading
import weakref
from collections.abc import AsyncIterator, Mapping
from typing import Any

from .transport import (
    ClientHandler,
    RawMessage,
    Transport,
    TransportClosedError,
    TransportState,
)

DART_PORT_ENV = "PYRITE_IDE_PLUGIN_BRIDGE_PORT"
DART_CHANNEL_LABEL_ENV = "PYRITE_IDE_PLUGIN_BRIDGE_LABEL"
DART_SESSION_TOKEN_ENV = "PYRITE_IDE_DART_SESSION_TOKEN"
DART_SESSION_TOKEN_LABEL = "__serious_python_dart_session__"
_CLOSE_MESSAGE = object()


class _QueueOverflowError(RuntimeError):
    pass


class _RestartRegistry:
    def __init__(self, bridge_module: Any):
        self._channels: weakref.WeakValueDictionary[
            str, DartBridgeTransport
        ] = weakref.WeakValueDictionary()
        self._dart_session_token: int | None = None
        bridge_module.add_session_restart_handler(self._handle_restart)

    def add(self, transport: DartBridgeTransport) -> None:
        token = transport.dart_session_token
        if token is not None:
            self._adopt_session(token)
        existing = self._channels.get(transport.channel_label)
        if existing is not None and existing is not transport:
            raise RuntimeError(
                f"Duplicate dart bridge channel label: {transport.channel_label}"
            )
        self._channels[transport.channel_label] = transport

    def remove(self, transport: DartBridgeTransport) -> None:
        existing = self._channels.get(transport.channel_label)
        if existing is transport:
            self._channels.pop(transport.channel_label, None)

    def _adopt_session(self, token: int) -> bool:
        previous = self._dart_session_token
        self._dart_session_token = token
        if previous is None or previous == token:
            return False
        for transport in list(self._channels.values()):
            transport._close_for_session_restart()
        return True

    def _handle_restart(self, ports: dict[str, int]) -> None:
        raw_token = ports.get(DART_SESSION_TOKEN_LABEL)
        if raw_token is not None and raw_token > 0:
            if self._adopt_session(int(raw_token)):
                return
        for label, transport in list(self._channels.items()):
            port = ports.get(label)
            if port is not None:
                transport._schedule_port_update(port)


_restart_registries: weakref.WeakKeyDictionary[Any, _RestartRegistry] = (
    weakref.WeakKeyDictionary()
)


def _restart_registry(bridge_module: Any) -> _RestartRegistry:
    registry = _restart_registries.get(bridge_module)
    if registry is None:
        registry = _RestartRegistry(bridge_module)
        _restart_registries[bridge_module] = registry
    return registry


class DartBridgeTransport(Transport):
    def __init__(
        self,
        port: int,
        channel_label: str,
        *,
        queue_size: int = 50,
        bridge_module: Any = None,
        dart_session_token: int | None = None,
    ):
        if port <= 0:
            raise ValueError("dart bridge port must be positive")
        if not channel_label:
            raise ValueError("dart bridge channel label must not be empty")
        if queue_size <= 0:
            raise ValueError("dart bridge queue size must be positive")
        if dart_session_token is not None and dart_session_token <= 0:
            raise ValueError("dart session token must be positive")

        if bridge_module is None:
            import dart_bridge as bridge_module

        self._bridge = bridge_module
        self._port = port
        self.channel_label = channel_label
        self.dart_session_token = dart_session_token
        self.queue_size = queue_size
        self._state = TransportState.CLOSED
        self._loop: asyncio.AbstractEventLoop | None = None
        self._queue: asyncio.Queue[RawMessage | object] | None = None
        self._closed_event: asyncio.Event | None = None
        self._handler_task: asyncio.Task[None] | None = None
        self._client = object()
        self._closed = False
        self._failure: BaseException | None = None
        self._native_lock = threading.Lock()
        self._native_handler = self._receive_native
        self._registry = _restart_registry(self._bridge)

    @classmethod
    def from_environment(
        cls,
        *,
        queue_size: int = 50,
        bridge_module: Any = None,
        environment: Mapping[str, str] | None = None,
    ) -> DartBridgeTransport:
        source = os.environ if environment is None else environment
        raw_port = source.get(DART_PORT_ENV)
        channel_label = source.get(DART_CHANNEL_LABEL_ENV)
        raw_session_token = source.get(DART_SESSION_TOKEN_ENV)
        if raw_port is None:
            raise RuntimeError(f"{DART_PORT_ENV} is required")
        if channel_label is None or not channel_label:
            raise RuntimeError(f"{DART_CHANNEL_LABEL_ENV} is required")
        if raw_session_token is None:
            raise RuntimeError(f"{DART_SESSION_TOKEN_ENV} is required")
        try:
            port = int(raw_port)
        except ValueError as error:
            raise RuntimeError(f"{DART_PORT_ENV} must be an integer") from error
        try:
            dart_session_token = int(raw_session_token)
        except ValueError as error:
            raise RuntimeError(
                f"{DART_SESSION_TOKEN_ENV} must be an integer"
            ) from error
        return cls(
            port,
            channel_label,
            queue_size=queue_size,
            bridge_module=bridge_module,
            dart_session_token=dart_session_token,
        )

    @property
    def port(self) -> int:
        return self._port

    @property
    def state(self) -> TransportState:
        return self._state

    async def start(self, handler: ClientHandler) -> None:
        if self._closed:
            raise TransportClosedError("DartBridgeTransport is closed")
        if self._state == TransportState.READY:
            return

        self._state = TransportState.CONNECTING
        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue(maxsize=self.queue_size)
        self._closed_event = asyncio.Event()
        native_registered = False
        try:
            self._registry.add(self)
            with self._native_lock:
                self._bridge.set_enqueue_handler_func(
                    self._port,
                    self._native_handler,
                )
                native_registered = True
            self._handler_task = asyncio.ensure_future(handler(self._client))
            self._handler_task.add_done_callback(self._handler_finished)
            self._state = TransportState.READY
        except BaseException as error:
            self._registry.remove(self)
            if native_registered:
                with contextlib.suppress(Exception):
                    with self._native_lock:
                        self._bridge.set_enqueue_handler_func(self._port, None)
            self._failure = error
            self._state = TransportState.FAILED
            if self._closed_event is not None:
                self._closed_event.set()
            raise

    def _handler_finished(self, task: asyncio.Future[None]) -> None:
        if not task.cancelled():
            with contextlib.suppress(asyncio.CancelledError):
                error = task.exception()
                if error is not None:
                    self._failure = error
                    self._state = TransportState.FAILED
        if not self._closed:
            self.close()

    def _receive_native(self, payload: bytes) -> None:
        loop = self._loop
        if self._closed or loop is None or loop.is_closed():
            return
        message = bytes(payload)
        with contextlib.suppress(RuntimeError):
            loop.call_soon_threadsafe(self._enqueue_on_loop, message)

    def _enqueue_on_loop(self, message: bytes) -> None:
        queue = self._queue
        if self._closed or queue is None:
            return
        try:
            queue.put_nowait(message)
        except asyncio.QueueFull:
            self._state = TransportState.FAILED
            self._replace_oldest(
                _QueueOverflowError(
                    f"Dart bridge queue for {self.channel_label} is full"
                )
            )

    def _replace_oldest(self, message: object) -> None:
        queue = self._queue
        if queue is None:
            return
        try:
            queue.get_nowait()
            queue.task_done()
        except asyncio.QueueEmpty:
            pass
        try:
            queue.put_nowait(message)
        except asyncio.QueueFull:
            pass

    async def _messages(self, client: Any) -> AsyncIterator[RawMessage]:
        if client is not self._client:
            raise ValueError("Unknown dart bridge client")
        queue = self._queue
        if queue is None:
            raise RuntimeError("DartBridgeTransport has not started")
        while True:
            message = await queue.get()
            try:
                if message is _CLOSE_MESSAGE:
                    return
                if isinstance(message, Exception):
                    raise message
                if isinstance(message, (str, bytes)):
                    yield message
            finally:
                queue.task_done()

    def messages(self, client: Any) -> AsyncIterator[RawMessage]:
        return self._messages(client)

    async def send(self, client: Any, message: RawMessage) -> None:
        if self._closed or self._state in {
            TransportState.CLOSING,
            TransportState.CLOSED,
        }:
            raise TransportClosedError("DartBridgeTransport is closed")
        if client is not self._client:
            raise ValueError("Unknown dart bridge client")
        payload = message.encode("utf-8") if isinstance(message, str) else bytes(message)
        try:
            self._bridge.send_bytes(self._port, payload)
        except BaseException as error:
            self._failure = error
            self._state = TransportState.FAILED
            self.close()
            raise

    async def wait_closed(self) -> None:
        event = self._closed_event
        if event is None:
            return
        await event.wait()
        task = self._handler_task
        if task is not None and task is not asyncio.current_task():
            with contextlib.suppress(asyncio.CancelledError):
                await task

    def _schedule_port_update(self, port: int) -> None:
        loop = self._loop
        if self._closed or loop is None or loop.is_closed():
            return
        with contextlib.suppress(RuntimeError):
            loop.call_soon_threadsafe(self._update_port_on_loop, int(port))

    def _close_for_session_restart(self) -> None:
        self.close()

    def _update_port_on_loop(self, port: int) -> None:
        with self._native_lock:
            if self._closed or port <= 0 or port == self._port:
                return
            self._bridge.set_enqueue_handler_func(self._port, None)
            if self._closed:
                return
            self._port = port
            self._bridge.set_enqueue_handler_func(
                self._port,
                self._native_handler,
            )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._state = TransportState.CLOSING
        self._registry.remove(self)
        try:
            with self._native_lock:
                self._bridge.set_enqueue_handler_func(self._port, None)
        except BaseException as error:
            self._failure = error

        loop = self._loop
        if loop is None or loop.is_closed():
            self._state = TransportState.CLOSED
            if self._closed_event is not None:
                self._closed_event.set()
            return
        try:
            loop.call_soon_threadsafe(self._finish_close_on_loop)
        except RuntimeError:
            self._state = TransportState.CLOSED
            if self._closed_event is not None:
                self._closed_event.set()

    def _finish_close_on_loop(self) -> None:
        self._replace_oldest(_CLOSE_MESSAGE)
        task = self._handler_task
        if task is not None and not task.done():
            task.cancel()
        self._state = TransportState.CLOSED
        if self._closed_event is not None:
            self._closed_event.set()
