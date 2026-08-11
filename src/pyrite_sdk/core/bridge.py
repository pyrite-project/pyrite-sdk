from __future__ import annotations

import asyncio
import inspect
import os
import sys
import threading
import time
import traceback
import queue
import weakref
from pydantic import ValidationError
from pathlib import Path
from typing import Any, Callable, Coroutine, Optional, TYPE_CHECKING
from ..models.consts import *
from ..models.schema import *
from .errors import api_error_from_payload
from .dart_bridge_transport import DartBridgeTransport
from .transport import Transport, TransportClosedError
from .context import (
    PLUGIN_CONTEXT_ENV_VARS,
    PluginContext,
    PluginContextError,
)

if TYPE_CHECKING:
    from ..interfaces.plugin import PluginType

LIFECYCLE_MAP: dict[LifecycleHook, str] = {
    LifecycleHook.START: "on_start",
    LifecycleHook.PAUSE: "on_pause",
    LifecycleHook.RESUME: "on_resume",
    LifecycleHook.DISPOSE: "on_dispose",
}
_STOP_MESSAGE = object()
PROTOCOL_VERSION = 1
SDK_CAPABILITIES = ["sdk.v1"]
MAX_LOG_BATCH_BYTES = 64 * 1024
OUTBOUND_DRAIN_BATCH_SIZE = 32


class BridgeOutputRouter:
    _stdout: Optional["BridgeOutputRouter"] = None
    _stderr: Optional["BridgeOutputRouter"] = None
    _routes: dict[int, "Bridge"] = {}
    _threading_patched: bool = False
    _route_lock = threading.RLock()

    def __init__(self, stream_name: str, original: Any) -> None:
        self.stream_name: str = stream_name
        self.original: Any = original
        self._buffers: dict[int, str] = {}

    @classmethod
    def install(cls) -> None:
        with cls._route_lock:
            if cls._stdout is None:
                cls._stdout = BridgeOutputRouter("stdout", sys.stdout)
                sys.stdout = cls._stdout
            if cls._stderr is None:
                cls._stderr = BridgeOutputRouter("stderr", sys.stderr)
                sys.stderr = cls._stderr
            cls._patch_threading()

    @classmethod
    def register_current_thread(cls, bridge: "Bridge") -> None:
        with cls._route_lock:
            if not getattr(bridge, "_output_redirected", False):
                return
            thread_id = threading.get_ident()
            if cls._routes.get(thread_id) is not bridge:
                cls._discard_buffers(thread_id)
            cls._routes[thread_id] = bridge

    @classmethod
    def unregister_current_thread(
        cls, bridge: Optional["Bridge"] = None
    ) -> None:
        thread_id = threading.get_ident()
        with cls._route_lock:
            current = cls._routes.get(thread_id)
            if current is None or (bridge is not None and current is not bridge):
                return
            cls._routes.pop(thread_id, None)
            cls._discard_buffers(thread_id)

    @classmethod
    def unregister_bridge(cls, bridge: "Bridge") -> None:
        with cls._route_lock:
            thread_ids = [
                thread_id
                for thread_id, current in cls._routes.items()
                if current is bridge
            ]
            for thread_id in thread_ids:
                cls._routes.pop(thread_id, None)
                cls._discard_buffers(thread_id)

    @classmethod
    def _discard_buffers(cls, thread_id: int) -> None:
        for router in (cls._stdout, cls._stderr):
            if isinstance(router, BridgeOutputRouter):
                router._buffers.pop(thread_id, None)

    @classmethod
    def current_bridge(cls) -> Optional["Bridge"]:
        with cls._route_lock:
            return cls._routes.get(threading.get_ident())

    @classmethod
    def _patch_threading(cls) -> None:
        if cls._threading_patched:
            return
        original_start = threading.Thread.start
        original_bootstrap_inner = threading.Thread._bootstrap_inner

        def start(thread: Any, *args: Any, **kwargs: Any) -> Any:
            bridge = cls.current_bridge()
            thread._pyrite_bridge = weakref.ref(bridge) if bridge is not None else None
            try:
                return original_start(thread, *args, **kwargs)
            except BaseException:
                thread._pyrite_bridge = None
                raise

        def bootstrap_inner(thread: Any, *args: Any, **kwargs: Any) -> Any:
            bridge_ref = getattr(thread, "_pyrite_bridge", None)
            try:
                if bridge_ref is not None:
                    bridge = bridge_ref()
                    if bridge is not None:
                        cls.register_current_thread(bridge)
                thread._pyrite_bridge = None
                bridge = None
                return original_bootstrap_inner(thread, *args, **kwargs)
            finally:
                cls.unregister_current_thread()
                thread._pyrite_bridge = None

        threading.Thread.start = start
        threading.Thread._bootstrap_inner = bootstrap_inner
        cls._threading_patched = True

    def write(self, text: str) -> int:
        self.original.write(text)
        self.original.flush()
        cls = type(self)
        with cls._route_lock:
            bridge = cls._routes.get(threading.get_ident())
            if bridge is None:
                return len(text)
            thread_id = threading.get_ident()
            buffer = self._buffers.get(thread_id, "") + text
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                bridge.emit_output(self.stream_name, line.rstrip("\r"))
            self._buffers[thread_id] = buffer
        return len(text)

    def flush(self) -> None:
        self.original.flush()
        cls = type(self)
        with cls._route_lock:
            bridge = cls._routes.get(threading.get_ident())
            if bridge is None:
                return
            thread_id = threading.get_ident()
            buffer = self._buffers.get(thread_id, "")
            if buffer:
                bridge.emit_output(self.stream_name, buffer)
                self._buffers[thread_id] = ""

    def isatty(self) -> bool:
        return self.original.isatty()

    @property
    def encoding(self) -> Optional[str]:
        return getattr(self.original, "encoding", None)


class Bridge:
    def __init__(
        self,
        plugin: PluginType,
        queue_size: int = 50,
        transport: Optional[Transport] = None,
    ) -> None:
        startup_environment = dict(os.environ)
        self.plugin = plugin
        self.running = True
        self.connected_clients: set[Any] = set()
        self.message_queue: Optional[asyncio.Queue[list[Any]]] = None
        # self.response_queue: Optional[asyncio.Queue] = None
        self.callbacks: dict[str, Callable[..., Any]] = {}
        self._pending_responses = 0
        self._stop_when_idle = False
        self._stop_requested = False
        self._defer_stop = False
        self._disposed = False
        self._lifecycle_lock = asyncio.Lock()
        self.asyncio_loop: Optional[asyncio.AbstractEventLoop] = None
        self.queue_size = queue_size
        if transport is None:
            if "PYRITE_IDE_PLUGIN_PORT" in startup_environment:
                raise RuntimeError(
                    "PYRITE_IDE_PLUGIN_PORT is no longer supported; "
                    "a native Dart bridge port and channel label are required"
                )
        self._context_is_host_managed = any(
            name in startup_environment for name in PLUGIN_CONTEXT_ENV_VARS
        )
        self._context = PluginContext.from_environment(
            startup_environment,
            allow_standalone=transport is not None,
        )
        if transport is None:
            transport = DartBridgeTransport.from_environment(
                queue_size=queue_size,
                environment=startup_environment,
            )
        self.transport = transport
        self._stdout = getattr(BridgeOutputRouter._stdout, "original", sys.stdout)
        self._stderr = getattr(BridgeOutputRouter._stderr, "original", sys.stderr)
        self._output_redirected = False
        self._pending_output: list[tuple[str, str]] = []
        self._outgoing_sequence = 0
        self._incoming_sequence = 0
        self._handshake_state = "pending"
        self._request_tasks: dict[str, asyncio.Task[None]] = {}
        self._reporting_error = False
        self._previous_loop_exception_handler: Optional[Callable[..., Any]] = None

    @property
    def context(self) -> PluginContext:
        return self._context

    @property
    def plugin_id(self) -> str:
        return self._context.id

    @property
    def session_id(self) -> str:
        return self._context.session_id

    @property
    def generation(self) -> int:
        return self._context.generation

    def _stamp(self, envelope: Envelope) -> Envelope:
        self._outgoing_sequence += 1
        envelope.protocol_version = PROTOCOL_VERSION
        envelope.plugin_id = self.plugin_id or "standalone"
        envelope.session_id = self.session_id
        envelope.generation = self.generation
        envelope.sequence = self._outgoing_sequence
        return envelope

    def report_error(
        self,
        message: str,
        *,
        traceback_text: Optional[str] = None,
        source: Optional[str] = None,
    ) -> None:
        if self._reporting_error or self._disposed:
            return
        self._reporting_error = True
        try:
            self.push(
                request(
                    "sdk.runtime.report_error",
                    payload={
                        "message": str(message),
                        "traceback": traceback_text,
                        "source": source,
                    },
                )
            )
        except Exception:
            self._log_internal("Failed to report plugin error")
        finally:
            self._reporting_error = False

    def _handle_loop_exception(
        self,
        loop: asyncio.AbstractEventLoop,
        context: dict[str, Any],
    ) -> None:
        error = context.get("exception")
        message = context.get("message") or "Unhandled asyncio exception"
        traceback_text = None
        if error is not None:
            traceback_text = "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            )
        self.report_error(
            message if error is None else f"{message}: {error}",
            traceback_text=traceback_text,
            source="asyncio",
        )

    async def _send_protocol_error(self, client: Any, message: str) -> None:
        await self.send(
            client,
            Envelope(
                type="sdk.response.error",
                payload={
                    "code": ErrorCode.PROTOCOL_ERROR.value,
                    "message": message,
                    "details": None,
                },
            ),
        )

    def _start_request_task(
        self,
        env: Envelope,
        operation: Coroutine[Any, Any, None],
    ) -> None:
        previous = self._request_tasks.get(env.request_id)
        if previous is not None and not previous.done():
            if inspect.iscoroutine(operation):
                operation.close()
            raise RuntimeError(f"Duplicate active request ID: {env.request_id}")
        task = asyncio.create_task(operation)
        self._request_tasks[env.request_id] = task

        def _done(completed: asyncio.Task[None]) -> None:
            if self._request_tasks.get(env.request_id) is completed:
                self._request_tasks.pop(env.request_id, None)
            if completed.cancelled():
                return
            try:
                error = completed.exception()
            except asyncio.CancelledError:
                return
            if error is not None:
                self._log_internal(
                    f"Unhandled request task error for {env.type}: {error}"
                )
                self.report_error(
                    f"Unhandled request task error for {env.type}: {error}",
                    traceback_text="".join(
                        traceback.format_exception(
                            type(error), error, error.__traceback__
                        )
                    ),
                    source=env.type,
                )

        task.add_done_callback(_done)

    def _cancel_request_task(self, request_id: str) -> bool:
        task = self._request_tasks.pop(request_id, None)
        if task is None or task.done():
            return False
        task.cancel()
        return True

    async def _cancel_all_request_tasks(self) -> None:
        tasks = list(self._request_tasks.values())
        self._request_tasks.clear()
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _run_lifecycle_request(
        self, env: Envelope, client: Any
    ) -> None:
        payload = LifecyclePayload(**env.payload)
        handler_name = LIFECYCLE_MAP.get(payload.hook)
        if handler_name is None:
            self.push(
                err(
                    env,
                    ErrorCode.API_NOT_FOUND,
                    f"Unknown lifecycle hook: {payload.hook}",
                ),
                client,
            )
            return
        self._defer_stop = True
        cancelled = False
        try:
            try:
                async with self._lifecycle_lock:
                    if self._disposed:
                        raise RuntimeError("Plugin is already disposed")
                    handler = getattr(self.plugin, handler_name)
                    result = handler()
                    if inspect.isawaitable(result):
                        await result
                    if payload.hook == LifecycleHook.DISPOSE:
                        events = getattr(self.plugin, "events", None)
                        if events is not None:
                            events.dispose_all()
                        commands = getattr(self.plugin, "commands", None)
                        if commands is not None:
                            commands.dispose_all()
                        views = getattr(self.plugin, "views", None)
                        if views is not None:
                            views.dispose_all()
                        self._fail_all_pending_responses(
                            TransportClosedError("Plugin is disposed")
                        )
                        self.callbacks.clear()
                response = ok(env)
            except asyncio.CancelledError:
                cancelled = True
                raise
            except Exception as error:
                response = err(
                    env,
                    ErrorCode.INTERNAL_ERROR,
                    str(error),
                    traceback.format_exc(),
                )
            await self.send(client, response)
            if payload.hook == LifecycleHook.DISPOSE:
                current = asyncio.current_task()
                for request_id, task in list(self._request_tasks.items()):
                    if task is current:
                        continue
                    self._request_tasks.pop(request_id, None)
                    if not task.done():
                        task.cancel()
                self._disposed = True
        finally:
            self._defer_stop = False
            if not cancelled and (
                payload.hook == LifecycleHook.DISPOSE or self._stop_requested
            ):
                self.stop()

    async def _run_command_request(
        self, env: Envelope, client: Any
    ) -> None:
        commands = getattr(self.plugin, "commands", None)
        try:
            if commands is None:
                raise LookupError("Plugin does not expose commands")
            result = await commands.dispatch(
                env.payload.get("commandId", ""),
                env.payload.get("args") or {},
                env.payload.get("context") or {},
            )
            self.push(ok(env, result), client)
        except asyncio.CancelledError:
            raise
        except LookupError as error:
            self.push(err(env, ErrorCode.KEY_NOT_FOUND, str(error)), client)
        except Exception as error:
            details = traceback.format_exc()
            self.report_error(
                str(error),
                traceback_text=details,
                source="ide.command.execute",
            )
            self.push(
                err(
                    env,
                    ErrorCode.INTERNAL_ERROR,
                    str(error),
                    traceback.format_exc(),
                ),
                client,
            )

    async def _run_context_menu_request(
        self, env: Envelope, client: Any
    ) -> None:
        views = getattr(self.plugin, "views", None)
        try:
            menu = (
                await views.handle_context_menu_request(env.payload)
                if views is not None
                else None
            )
            self.push(ok(env, menu), client)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            details = traceback.format_exc()
            self.report_error(
                str(error),
                traceback_text=details,
                source="ide.view.contextMenu.request",
            )
            self.push(
                err(
                    env,
                    ErrorCode.INTERNAL_ERROR,
                    str(error),
                    traceback.format_exc(),
                ),
                client,
            )

    def redirect_output(self) -> None:
        BridgeOutputRouter.install()
        self._output_redirected = True
        BridgeOutputRouter.register_current_thread(self)

    def _stop_output_routing(self) -> None:
        self._output_redirected = False
        BridgeOutputRouter.unregister_bridge(self)

    def emit_output(self, stream: str, text: str) -> None:
        if not text:
            return
        if self.asyncio_loop is None or self.message_queue is None:
            self._pending_output.append((stream, text))
            return
        for chunk in self._chunk_output_text(text):
            self.push(
                request(
                    "sdk.output.append",
                    {
                        "plugin_id": self.plugin_id,
                        "stream": stream,
                        "text": chunk,
                    },
                )
            )

    @staticmethod
    def _chunk_output_text(text: str) -> list[str]:
        if len(text.encode("utf-8")) <= MAX_LOG_BATCH_BYTES:
            return [text]
        chunks: list[str] = []
        current: list[str] = []
        current_bytes = 0
        for character in text:
            encoded_bytes = len(character.encode("utf-8"))
            if current and current_bytes + encoded_bytes > MAX_LOG_BATCH_BYTES:
                chunks.append("".join(current))
                current = []
                current_bytes = 0
            current.append(character)
            current_bytes += encoded_bytes
        if current:
            chunks.append("".join(current))
        return chunks

    def _log_internal(self, *values: Any) -> None:
        print(*values, file=self._stdout, flush=True)

    def flush_pending_output(self) -> None:
        if not self._pending_output:
            return
        pending = self._pending_output
        self._pending_output = []
        for stream, text in pending:
            self.emit_output(stream, text)

    async def handler(self, client: Any) -> None:
        if self.plugin is None:
            raise RuntimeError(
                "Bridge.start(plugin) must be called "
                "before accepting transport connections"
            )

        self.connected_clients.add(client)
        incoming_sequence = 0

        try:
            async for raw in self.transport.messages(client):
                try:
                    env = Envelope.model_validate_json(raw)
                except ValidationError as error:
                    await self._send_protocol_error(
                        client,
                        f"Incompatible or malformed protocol envelope: {error}",
                    )
                    continue

                if env.protocol_version != PROTOCOL_VERSION:
                    await self._send_protocol_error(
                        client,
                        f"Unsupported protocolVersion: {env.protocol_version}",
                    )
                    continue
                if env.sequence <= incoming_sequence:
                    await self._send_protocol_error(
                        client,
                        f"Duplicate or out-of-order sequence: {env.sequence}",
                    )
                    continue

                if env.type == "ide.initialize":
                    if self._handshake_state != "pending":
                        await self._send_protocol_error(
                            client,
                            "ide.initialize received after handshake started",
                        )
                        continue
                    requested_version = env.payload.get("protocolVersion")
                    if requested_version != PROTOCOL_VERSION:
                        await self._send_protocol_error(
                            client,
                            f"Unsupported protocolVersion: {requested_version}",
                        )
                        continue
                    if env.plugin_id != self.plugin_id:
                        await self._send_protocol_error(
                            client,
                            "pluginId does not match the launched plugin",
                        )
                        continue
                    handshake_context = None
                    if self._context_is_host_managed:
                        try:
                            handshake_context = PluginContext.from_handshake_payload(
                                env.payload.get("pluginContext")
                            )
                        except PluginContextError as error:
                            await self._send_protocol_error(client, str(error))
                            continue
                        startup_paths = (
                            self._context.plugin_dir,
                            self._context.data_dir,
                            self._context.cache_dir,
                            self._context.temp_dir,
                        )
                        handshake_paths = (
                            handshake_context.plugin_dir,
                            handshake_context.data_dir,
                            handshake_context.cache_dir,
                            handshake_context.temp_dir,
                        )
                        if (
                            handshake_context.id != self.plugin_id
                            or handshake_context.session_id != self.session_id
                            or handshake_context.generation != self.generation
                            or handshake_paths != startup_paths
                        ):
                            await self._send_protocol_error(
                                client,
                                "ide.initialize pluginContext does not match "
                                "the startup context",
                            )
                            continue
                        if (
                            env.plugin_id != handshake_context.id
                            or env.session_id != handshake_context.session_id
                            or env.generation != handshake_context.generation
                        ):
                            await self._send_protocol_error(
                                client,
                                "ide.initialize envelope does not match "
                                "pluginContext",
                            )
                            continue
                    payload_plugin_id = env.payload.get("pluginId")
                    if (
                        self._context_is_host_managed
                        and payload_plugin_id is not None
                        and payload_plugin_id != self.plugin_id
                    ):
                        await self._send_protocol_error(
                            client,
                            "ide.initialize payload pluginId does not match "
                            "the startup context",
                        )
                        continue
                    if self._context_is_host_managed and (
                        env.session_id != self.session_id
                        or env.generation != self.generation
                    ):
                        await self._send_protocol_error(
                            client,
                            "ide.initialize sessionId or generation does not "
                            "match the startup context",
                        )
                        continue
                    try:
                        updated_context = self._context.with_handshake(
                            session_id=env.session_id,
                            generation=env.generation,
                            capabilities=(
                                handshake_context.capabilities
                                if handshake_context is not None
                                else env.payload.get("capabilities")
                            ),
                        )
                    except PluginContextError as error:
                        await self._send_protocol_error(client, str(error))
                        continue
                    incoming_sequence = env.sequence
                    self._incoming_sequence = env.sequence
                    self._context = updated_context
                    self._handshake_state = "initialized"
                    await self.send(
                        client,
                        Envelope(
                            type="sdk.initialize",
                            payload={
                                "protocolVersion": PROTOCOL_VERSION,
                                "sdkVersion": "1.1.0",
                                "capabilities": SDK_CAPABILITIES,
                            },
                            reply_to=env.request_id,
                        ),
                    )
                    continue

                if env.type == "ide.initialized":
                    if self._handshake_state != "initialized":
                        await self._send_protocol_error(
                            client,
                            "ide.initialized received before ide.initialize",
                        )
                        continue
                    if (
                        env.plugin_id != self.plugin_id
                        or env.session_id != self.session_id
                        or env.generation != self.generation
                    ):
                        await self._send_protocol_error(
                            client,
                            "ide.initialized does not match the active "
                            "plugin session",
                        )
                        continue
                    if env.payload.get("protocolVersion") != PROTOCOL_VERSION:
                        await self._send_protocol_error(
                            client,
                            "ide.initialized has an incompatible protocolVersion",
                        )
                        continue
                    try:
                        updated_context = self._context.with_handshake(
                            session_id=env.session_id,
                            generation=env.generation,
                            capabilities=(
                                self._context.capabilities
                                if self._context_is_host_managed
                                else env.payload.get("capabilities")
                            ),
                        )
                    except PluginContextError as error:
                        await self._send_protocol_error(client, str(error))
                        continue
                    incoming_sequence = env.sequence
                    self._incoming_sequence = env.sequence
                    self._context = updated_context
                    self._handshake_state = "ready"
                    await self.send(
                        client,
                        Envelope(
                            type="sdk.ready",
                            payload={"capabilities": SDK_CAPABILITIES},
                            reply_to=env.request_id,
                        ),
                    )
                    continue

                if self._handshake_state != "ready":
                    await self._send_protocol_error(
                        client,
                        f"Business message before sdk.ready: {env.type}",
                    )
                    continue

                if (
                    env.plugin_id != self.plugin_id
                    or env.session_id != self.session_id
                    or env.generation != self.generation
                ):
                    await self._send_protocol_error(
                        client,
                        "Stale or mismatched plugin session",
                    )
                    continue
                incoming_sequence = env.sequence
                self._incoming_sequence = env.sequence
                if env.type == "ide.request.cancel":
                    request_id = str(env.payload.get("requestId") or "")
                    if request_id:
                        self._cancel_request_task(request_id)
                    continue
                if env.deadline is not None and env.deadline <= int(time.time() * 1000):
                    self.push(
                        err(
                            env,
                            ErrorCode.TIMEOUT,
                            "Request deadline exceeded before execution",
                        ),
                        client,
                    )
                    continue
                if env.data:
                    pass
                else:
                    match env.type:
                        case "ide.lifecycle.hook":
                            self._start_request_task(
                                env,
                                self._run_lifecycle_request(env, client),
                            )
                            await asyncio.sleep(0)

                        case "ide.command.execute":
                            self._start_request_task(
                                env,
                                self._run_command_request(env, client),
                            )
                            await asyncio.sleep(0)

                        case "ide.event.emit":
                            events = getattr(self.plugin, "events", None)
                            if events is not None:
                                await events.dispatch(
                                    env.payload.get("subscriptionId", ""),
                                    env.payload.get("topic", ""),
                                    env.payload.get("events", []),
                                )

                        case "ide.health.ping":
                            self.push(
                                Envelope(
                                    type="sdk.health.pong",
                                    payload={
                                        "status": "ok",
                                        "activeRequestTasks": len(self._request_tasks),
                                        "pendingResponses": self._pending_responses,
                                    },
                                    reply_to=env.request_id,
                                ),
                                client,
                            )

                        case "ide.view.contextMenu.request":
                            self._start_request_task(
                                env,
                                self._run_context_menu_request(env, client),
                            )
                            await asyncio.sleep(0)

                        case (
                            "ide.view.ack"
                            | "ide.view.nack"
                            | "ide.view.resync"
                            | "ide.view.event"
                            | "ide.view.visibility.changed"
                            | "ide.view.route.sync"
                        ):
                            views = getattr(self.plugin, "views", None)
                            if views is not None:
                                try:
                                    views.handle_frame(env.type, env.payload)
                                except Exception as error:
                                    self.report_error(
                                        str(error),
                                        traceback_text=traceback.format_exc(),
                                        source=env.type,
                                    )

                        case "ide.env.changed":
                            environment = getattr(self.plugin, "env", None)
                            if environment is not None:
                                environment._handle_change(env.payload or {})

                if env.reply_to and env.reply_to in self.callbacks:
                    data = env.payload or env.data or {}
                    if env.type.endswith(".response.error"):
                        payload = data if isinstance(data, dict) else {}
                        self._complete_pending_response(
                            env.reply_to,
                            error=api_error_from_payload(payload),
                        )
                    else:
                        self._complete_pending_response(
                            env.reply_to,
                            data=data,
                        )
                elif env.reply_to:
                    self._log_internal(
                        f"[DEBUG] reply_to={env.reply_to} not found in callbacks, type={env.type}"
                    )
        except TransportClosedError:
            self._log_internal("Transport connection closed")
            self.connected_clients.discard(client)
        except Exception:
            self._log_internal("Bridge handler error:\n", traceback.format_exc())
            self.connected_clients.discard(client)
        finally:
            await self._cancel_all_request_tasks()
            self.connected_clients.discard(client)

    async def send(self, client: Any, envelope: Envelope) -> None:
        try:
            self._stamp(envelope)
            if envelope.type != "sdk.output.append":
                self._log_internal("Sending:", envelope.type)
            await self.transport.send(
                client,
                envelope.model_dump_json(by_alias=True),
            )
        except TransportClosedError:
            self._log_internal("Transport connection closed")
            self.connected_clients.discard(client)
        except Exception as e:
            self._log_internal(f"Error in send: {e}")

    async def send_all(self, envelope: Envelope) -> None:
        for client in self.connected_clients.copy():
            await self.send(client, envelope)

    def push(
        self,
        envelope: Envelope,
        client: Any = None,
        on_error: Optional[Callable[[BaseException], Any]] = None,
    ) -> bool:
        if self._disposed:
            error = TransportClosedError("Plugin is disposed")
            if on_error is not None:
                on_error(error)
            return False
        loop = self.asyncio_loop
        if loop is None or loop.is_closed() or self.message_queue is None:
            self._log_internal("Error: cannot find loop")
            if on_error is not None:
                on_error(TransportClosedError("Plugin message loop is closed"))
            return False

        def _put() -> None:
            message_queue = self.message_queue
            if message_queue is None:
                if on_error is not None:
                    on_error(TransportClosedError("Plugin message loop is closed"))
                return
            try:
                message_queue.put_nowait([client, envelope])
            except asyncio.QueueFull:
                if envelope.type != "sdk.output.append":
                    self._log_internal("Warning: Message queue was full")
                if on_error is not None:
                    on_error(
                        RuntimeError(f"Plugin message queue is full: {envelope.type}")
                    )

        try:
            loop.call_soon_threadsafe(_put)
        except RuntimeError:
            self._log_internal("Error: plugin loop is closed")
            if on_error is not None:
                on_error(TransportClosedError("Plugin message loop is closed"))
            return False
        return True

    def _complete_pending_response(
        self,
        request_id: str,
        *,
        data: Any = None,
        error: BaseException | None = None,
    ) -> bool:
        callback = self.callbacks.pop(request_id, None)
        if callback is None:
            return False
        try:
            if error is not None:
                callback(error=error)
            elif isinstance(data, dict):
                callback(**data)
            else:
                callback(data)
            self._log_internal("[DEBUG] Callback invoked successfully")
        except Exception as callback_error:
            self._log_internal(f"Error in callback: {callback_error}")
        finally:
            self._pending_responses = max(0, self._pending_responses - 1)
            if self._stop_when_idle and self._pending_responses == 0:
                self.stop()
        return True

    def _cancel_pending_response(self, request_id: str) -> bool:
        if self.callbacks.pop(request_id, None) is None:
            return False
        self._pending_responses = max(0, self._pending_responses - 1)
        if self._stop_when_idle and self._pending_responses == 0:
            self.stop()
        return True

    def _fail_all_pending_responses(self, error: BaseException) -> None:
        request_ids = list(self.callbacks)
        for request_id in request_ids:
            self._complete_pending_response(request_id, error=error)

    def push_wait_response(
        self,
        envelope: Envelope,
        callback: Optional[Callable[..., Any]] = None,
        client: Any = None,
    ) -> bool:
        env_id = envelope.request_id
        if env_id in self.callbacks:
            raise ValueError(f"Duplicate pending request ID: {env_id}")
        self._pending_responses += 1
        self.callbacks[env_id] = callback or (lambda **_: None)
        return self.push(
            envelope,
            client,
            on_error=lambda error: self._complete_pending_response(
                env_id,
                error=error,
            ),
        )

    def stop_when_idle(self) -> None:
        self._stop_when_idle = True
        if self._pending_responses == 0:
            self.stop()

    def request_path(self, scope: PathScope, timeout: float = 5.0) -> Path:
        waiter: queue.Queue[Path | BaseException] = queue.Queue(maxsize=1)
        envelope = request(
            "sdk.path.request",
            PathRequestPayload(scope=scope),
        )

        def receive_path(
            path: str | None = None,
            error: BaseException | None = None,
            **_: Any,
        ) -> None:
            if error is not None:
                result: Path | BaseException = error
            elif path:
                result = Path(path)
            else:
                result = RuntimeError(
                    f"Host returned no plugin path for: {scope.value}"
                )
            try:
                waiter.put_nowait(result)
            except queue.Full:
                pass

        self.push_wait_response(envelope, callback=receive_path)
        try:
            result = waiter.get(timeout=timeout)
        except queue.Empty as exc:
            self._cancel_pending_response(envelope.request_id)
            raise TimeoutError(
                f"Timed out waiting for plugin path: {scope.value}"
            ) from exc
        if isinstance(result, BaseException):
            raise result
        return result

    async def loop(self) -> None:
        while True:
            assert self.message_queue is not None
            batch = [await self.message_queue.get()]
            for _ in range(OUTBOUND_DRAIN_BATCH_SIZE - 1):
                try:
                    batch.append(self.message_queue.get_nowait())
                except asyncio.QueueEmpty:
                    break
            should_stop = False
            for client, envelope in batch:
                try:
                    if envelope is _STOP_MESSAGE:
                        should_stop = True
                        continue
                    if client:
                        await self.send(client, envelope)
                    else:
                        await self.send_all(envelope)
                except Exception as e:
                    self._log_internal(f"Error in loop: {e}")
                finally:
                    self.message_queue.task_done()
            if should_stop:
                break
            await asyncio.sleep(0)
        self._log_internal("Plugin transport closed")

    async def main(self) -> None:
        self.message_queue = asyncio.Queue(maxsize=self.queue_size)
        # self.response_queue = asyncio.Queue(maxsize=self.queue_size)
        self.asyncio_loop = asyncio.get_running_loop()
        self._previous_loop_exception_handler = (
            self.asyncio_loop.get_exception_handler()
        )
        self.asyncio_loop.set_exception_handler(self._handle_loop_exception)
        self.flush_pending_output()
        try:
            await self.transport.start(self.handler)
            self._log_internal("Plugin transport started")
            transport_closed = asyncio.create_task(self.transport.wait_closed())
            message_loop = asyncio.create_task(self.loop())
            done, _ = await asyncio.wait(
                (transport_closed, message_loop),
                return_when=asyncio.FIRST_COMPLETED,
            )
            if transport_closed in done and not message_loop.done():
                assert self.message_queue is not None
                await self.message_queue.put([None, _STOP_MESSAGE])
            if message_loop in done and not transport_closed.done():
                self.transport.close()
            results = await asyncio.gather(
                transport_closed,
                message_loop,
                return_exceptions=True,
            )
            for result in results:
                if isinstance(result, BaseException) and not isinstance(
                    result,
                    asyncio.CancelledError,
                ):
                    raise result
        finally:
            if self.asyncio_loop is not None and not self.asyncio_loop.is_closed():
                self.asyncio_loop.set_exception_handler(
                    self._previous_loop_exception_handler
                )
            self._previous_loop_exception_handler = None
            await self._cancel_all_request_tasks()
            self.transport.close()
            self._fail_all_pending_responses(
                TransportClosedError("Plugin transport closed")
            )
            self.asyncio_loop = None
            self.message_queue = None
            self._stop_output_routing()

    def start(self) -> None:
        try:
            self.redirect_output()
            if sys.platform == "win32":
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            asyncio.run(self.main())
        except KeyboardInterrupt:
            self.running = False
        finally:
            self._stop_output_routing()

    def stop(self) -> None:
        self._stop_requested = True
        self.running = False
        self._stop_output_routing()
        if self._defer_stop:
            return
        loop = self.asyncio_loop
        if loop is None or loop.is_closed():
            return

        def _stop_on_loop() -> None:
            self.transport.close()
            if self.message_queue is not None:
                try:
                    self.message_queue.put_nowait([None, _STOP_MESSAGE])
                except asyncio.QueueFull:
                    asyncio.create_task(self.message_queue.put([None, _STOP_MESSAGE]))

        try:
            loop.call_soon_threadsafe(_stop_on_loop)
        except RuntimeError:
            return
