from __future__ import annotations

import asyncio
import websockets
import os
import sys
import threading
import traceback
import queue
from pathlib import Path
from typing import Optional, Callable, TYPE_CHECKING
from ..models.consts import *
from ..models.schema import *
from ..api.ui.sentence.var import Var
from ..interfaces.ui import PageType
from ..utils.ui import RFWSerializable, to_data
from ..api.ui.widgets.base import Widget

if TYPE_CHECKING:
    from ..interfaces.plugin import PluginType

LIFECYCLE_MAP: dict[LifecycleHook, Callable] = {
    LifecycleHook.START: lambda self: self.plugin.on_start(),
    LifecycleHook.PAUSE: lambda self: self.plugin.on_pause(),
    LifecycleHook.RESUME: lambda self: self.plugin.on_resume(),
    LifecycleHook.DISPOSE: lambda self: self.plugin.on_dispose(),
}


class BridgeOutputRouter:
    _stdout = None
    _stderr = None
    _routes: dict[int, "Bridge"] = {}
    _threading_patched = False

    def __init__(self, stream_name: str, original):
        self.stream_name = stream_name
        self.original = original
        self._buffers: dict[int, str] = {}

    @classmethod
    def install(cls):
        if cls._stdout is None:
            cls._stdout = BridgeOutputRouter("stdout", sys.stdout)
            sys.stdout = cls._stdout
        if cls._stderr is None:
            cls._stderr = BridgeOutputRouter("stderr", sys.stderr)
            sys.stderr = cls._stderr
        cls._patch_threading()

    @classmethod
    def register_current_thread(cls, bridge: "Bridge"):
        cls._routes[threading.get_ident()] = bridge

    @classmethod
    def current_bridge(cls):
        return cls._routes.get(threading.get_ident())

    @classmethod
    def _patch_threading(cls):
        if cls._threading_patched:
            return
        original_start = threading.Thread.start
        original_run = threading.Thread.run

        def start(thread, *args, **kwargs):
            thread._pyrite_bridge = cls.current_bridge()
            return original_start(thread, *args, **kwargs)

        def run(thread, *args, **kwargs):
            bridge = getattr(thread, "_pyrite_bridge", None)
            if bridge is not None:
                cls.register_current_thread(bridge)
            return original_run(thread, *args, **kwargs)

        threading.Thread.start = start
        threading.Thread.run = run
        cls._threading_patched = True

    def write(self, text: str):
        self.original.write(text)
        self.original.flush()
        bridge = self.current_bridge()
        if bridge is None:
            return len(text)
        thread_id = threading.get_ident()
        buffer = self._buffers.get(thread_id, "") + text
        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            bridge.emit_output(self.stream_name, line.rstrip("\r"))
        self._buffers[thread_id] = buffer
        return len(text)

    def flush(self):
        self.original.flush()
        bridge = self.current_bridge()
        if bridge is None:
            return
        thread_id = threading.get_ident()
        buffer = self._buffers.get(thread_id, "")
        if buffer:
            bridge.emit_output(self.stream_name, buffer)
            self._buffers[thread_id] = ""

    def isatty(self):
        return self.original.isatty()

    @property
    def encoding(self):
        return getattr(self.original, "encoding", None)


class Bridge:
    def __init__(self, plugin: PluginType, queue_size: int = 50):
        self.plugin = plugin
        self.running = True
        self.connected_clients = set()
        self.message_queue: Optional[asyncio.Queue] = None
        # self.response_queue: Optional[asyncio.Queue] = None
        self.callbacks: dict[str, Callable[[dict], Any]] = {}
        self._pending_responses = 0
        self._stop_when_idle = False
        self._path_responses: dict[str, queue.Queue[Path]] = {}
        self.asyncio_loop: Optional[asyncio.AbstractEventLoop] = None
        self.queue_size = queue_size
        self.port = int(os.environ.get("PYRITE_IDE_PLUGIN_PORT"))  # type: ignore
        self.plugin_id = os.environ.get("PYRITE_IDE_PLUGIN_ID", "")
        self._stdout = getattr(BridgeOutputRouter._stdout, "original", sys.stdout)
        self._stderr = getattr(BridgeOutputRouter._stderr, "original", sys.stderr)
        self._output_redirected = False
        self._pending_output: list[tuple[str, str]] = []
        self._callback_binding_names: set[str] = set()
        self.pushed_data = {}

    def redirect_output(self):
        BridgeOutputRouter.install()
        BridgeOutputRouter.register_current_thread(self)
        self._output_redirected = True

    def emit_output(self, stream: str, text: str):
        if not text:
            return
        if self.asyncio_loop is None or self.message_queue is None:
            self._pending_output.append((stream, text))
            return
        self.push(
            request(
                "sdk.output.append",
                {"plugin_id": self.plugin_id, "stream": stream, "text": text},
            )
        )

    def _log_internal(self, *values):
        print(*values, file=self._stdout)

    def flush_pending_output(self):
        if not self._pending_output:
            return
        pending = self._pending_output
        self._pending_output = []
        for stream, text in pending:
            self.emit_output(stream, text)

    async def handler(self, websocket):
        if self.plugin is None:
            raise RuntimeError(
                "Bridge.start(plugin) must be called "
                "before accepting websocket connections"
            )

        self.connected_clients.add(websocket)
        self.push(
            request("sdk.path.request", PathRequestPayload(scope=PathScope.ASSETS)),
            websocket,
        )

        try:
            async for raw in websocket:
                env = Envelope.parse_raw(raw)
                if env.data:
                    pass
                else:
                    match env.type:
                        case "ide.page.refresh":
                            self.refresh()
                            self.push(ok(env), websocket)

                        case "ide.event.callback":
                            payload = EventCallbackPayload(**env.payload)
                            _page: Optional[PageType] = self.plugin.pages.get(payload.page)
                            if not _page:
                                self.push(err(env, ErrorCode.KEY_NOT_FOUND,
                                            f"Page '{payload.page}' not found"), websocket)
                                return
                            page: PageType = _page
                            event = page.events.get(payload.name)
                            if not event:
                                if payload.name in self._callback_binding_names:
                                    self.push(ok(env), websocket)
                                    return
                                self.push(err(env, ErrorCode.KEY_NOT_FOUND,
                                            f"Event '{payload.name}' not found"), websocket)
                                return
                            try:
                                event(**payload.args)
                                self.push(ok(env), websocket)
                            except Exception as e:
                                self.push(err(env, ErrorCode.INTERNAL_ERROR, str(e)), websocket)

                        case "ide.lifecycle.hook":
                            payload = LifecyclePayload(**env.payload)
                            handler = LIFECYCLE_MAP.get(payload.hook)
                            if handler:
                                try:
                                    handler(self)
                                    self.push(ok(env), websocket)
                                except Exception as e:
                                    self.push(
                                        err(
                                            env,
                                            ErrorCode.INTERNAL_ERROR,
                                            str(e),
                                            traceback.format_exc(),
                                        ),
                                        websocket,
                                    )
                            else:
                                self.push(err(env, ErrorCode.API_NOT_FOUND,
                                            f"Unknown lifecycle hook: {payload.hook}"), websocket)

                        case "ide.response.path":
                            payload = PathResponsePayload(**env.payload)
                            response_plugin_id = env.payload.get("plugin_id", "") if env.payload else ""
                            if response_plugin_id and self.plugin_id and response_plugin_id != self.plugin_id:
                                self._log_internal(
                                    f"Warning: ignored path response for plugin {response_plugin_id}, current {self.plugin_id}"
                                )
                                continue
                            if payload.path:
                                if payload.scope == PathScope.ASSETS:
                                    self.plugin.assets = Path(payload.path)
                                    self.refresh()
                                waiter = self._path_responses.pop(payload.scope.value, None)
                                if waiter is not None:
                                    waiter.put(Path(payload.path))
                            else:
                                self._log_internal("Warning: path response missing path")

                        case "ide.router.sync":
                            payload = RouterSyncPayload(**env.payload)
                            self.plugin.router._sync(payload.page, payload.stack)
                
                if env.reply_to and env.reply_to in self.callbacks:
                    callback = self.callbacks.pop(env.reply_to)
                    try:
                        data = env.payload or env.data or {}
                        self._log_internal(f"[DEBUG] Invoking callback for reply_to={env.reply_to}, type={env.type}, data={data}")
                        callback(**data) if isinstance(data, dict) else callback(data)
                        self._log_internal(f"[DEBUG] Callback invoked successfully")
                    except Exception as e:
                        self._log_internal(f"Error in callback: {e}")
                    finally:
                        self._pending_responses = max(0, self._pending_responses - 1)
                        if self._stop_when_idle and self._pending_responses == 0:
                            self.stop()
                elif env.reply_to:
                    self._log_internal(f"[DEBUG] reply_to={env.reply_to} not found in callbacks, type={env.type}")
        except websockets.exceptions.ConnectionClosed:
            self._log_internal("Connection closed")
            self.connected_clients.discard(websocket)

    async def send(self, websocket, envelope: Envelope):
        try:
            if envelope.type != "sdk.output.append":
                self._log_internal("Sending:", envelope.type)
            await websocket.send(envelope.json())
        except websockets.exceptions.ConnectionClosed:
            self._log_internal("Connection closed")
            self.connected_clients.discard(websocket)
        except Exception as e:
            self._log_internal(f"Error in send: {e}")

    async def send_all(self, envelope: Envelope):
        for client in self.connected_clients.copy():
            await self.send(client, envelope)

    def refresh(self, call_on_refresh: bool = True):
        self.clear_callback_binding()
        Widget.next_widget_id = 0
        if call_on_refresh:
            self.plugin.on_refresh()
        if not hasattr(self.plugin, "pages"):
            self._log_internal("Warning: Plugin has no pages to refresh")
            return
        if not self.plugin.pages:
            self._log_internal("Warning: Plugin has empty pages to refresh")
            return
        for binding in Widget.callback_binding_names:
            data_var = binding[-2]
            if data_var not in self.pushed_data:
                self.let(data_var, binding[-1])
            self.register_callback_binding(*binding[:3])
        try:
            self.push(
                request(
                    "sdk.page.push",
                    PagePayload(
                        pages={
                            name: page.to_rfw()
                            for name, page in self.plugin.pages.items()
                        },
                    ),
                )
            )
        except Exception as e:
            self._log_internal("Error in refreshing pages:", e)

    def push(self, envelope: Envelope, client=None):
        if self.asyncio_loop is None or self.message_queue is None:
            self._log_internal("Error: cannot find loop")
            return

        def _put():
            assert self.message_queue is not None
            try:
                self.message_queue.put_nowait([client, envelope])
            except asyncio.QueueFull:
                if envelope.type != "sdk.output.append":
                    self._log_internal("Warning: Message queue was full")

        self.asyncio_loop.call_soon_threadsafe(_put)

    def push_wait_response(self, envelope: Envelope,
                           callback: Optional[Callable[[dict], Any]]=None,
                           client=None):
        env_id = envelope.id
        self._pending_responses += 1
        self.callbacks[env_id] = callback or (lambda **_: None)
        self.push(envelope, client)

    def stop_when_idle(self):
        self._stop_when_idle = True
        if self._pending_responses == 0:
            self.stop()

    def request_path(self, scope: PathScope, timeout: float = 5.0) -> Path:
        if self.plugin.assets is not None and scope == PathScope.PLUGIN:
            return self.plugin.assets
        waiter: queue.Queue[Path] = queue.Queue(maxsize=1)
        self._path_responses[scope.value] = waiter
        self.push(request("sdk.path.request", PathRequestPayload(scope=scope)))
        try:
            return waiter.get(timeout=timeout)
        except queue.Empty as exc:
            raise TimeoutError(f"Timed out waiting for plugin path: {scope.value}") from exc

    def let(self, name: Var, value: Any):
        var_name = self._to_var_name(name)
        self._log_internal(f"[DEBUG] let() called: name={var_name}, value={value}")
        self.pushed_data[var_name] = value
        self.push(
            request(
                "sdk.var.set",
                VarSetPayload(
                    name=var_name,
                    value=to_data(value),
                ),
            )
        )
        self._log_internal(f"[DEBUG] let() pushed sdk.var.set to queue")
    
    def clear_callback_binding(self):
        self._callback_binding_names.clear()
        Widget.callback_binding_names.clear()
        self.push(request("sdk.callback.clear"))

    def register_callback_binding(self, widget, event: str, var: Var):
        widget_id = getattr(widget, "widget_id")
        event_name = f"callback_{widget_id}_{event}"
        self._bind_widget_callback_event(widget, event, event_name)
        self._callback_binding_names.add(event_name)
        self.push(
            request(
                "sdk.callback.register",
                CallbackBindingPayload(
                    name=event_name,
                    var=self._to_var_name(var),
                ),
            )
        )

    def _bind_widget_callback_event(self, widget, event: str, event_name: str):
        current = widget.args.get(event)
        if current is None:
            widget.args[event] = _CallbackEvent(event_name)
            return
        if hasattr(current, "event"):
            previous_name = current.event
            current.event = event_name
            if hasattr(current, "_explicit_event"):
                current._explicit_event = True
            events = getattr(current, "events", None)
            if events is not None and previous_name in events:
                events[event_name] = events.pop(previous_name)

    def _to_var_name(self, name: Var) -> str:
        paths = list(name.paths)
        if paths and paths[0] in {"data", "args", "state"}:
            paths.pop(0)
        return Var(*paths).to_rfw()

    async def loop(self):
        while self.running:
            assert self.message_queue is not None
            client, envelope = await self.message_queue.get()
            try:
                if client:
                    await self.send(client, envelope)
                else:
                    await self.send_all(envelope)
            except Exception as e:
                self._log_internal(f"Error in loop: {e}")
            finally:
                self.message_queue.task_done()
        self.server.close()
        self._log_internal("Server closed")

    async def main(self):
        self.message_queue = asyncio.Queue(maxsize=self.queue_size)
        # self.response_queue = asyncio.Queue(maxsize=self.queue_size)
        self.asyncio_loop = asyncio.get_running_loop()
        self.flush_pending_output()
        async with websockets.serve(self.handler, "localhost", self.port) as self.server:
            self._log_internal(f"Server started on ws://localhost:{self.port}")
            await asyncio.gather(self.server.wait_closed(), self.loop())

    def start(self):
        try:
            self.redirect_output()
            if sys.platform == 'win32':
                asyncio.set_event_loop_policy(
                    asyncio.WindowsSelectorEventLoopPolicy()
                )
            asyncio.run(self.main())
        except KeyboardInterrupt:
            self.running = False

    def stop(self):
        self.running = False
        if self.server is not None:
            self.server.close()


class _CallbackEvent(RFWSerializable):
    def __init__(self, name: str) -> None:
        self.name = name

    def to_rfw(self) -> str:
        return f'event "{self.name}" {{}}'
