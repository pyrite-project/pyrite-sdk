from __future__ import annotations

import asyncio
import websockets
import os
import sys
from pathlib import Path
from typing import Optional, Callable, TYPE_CHECKING
from ..models.consts import *
from ..models.schema import *
from ..api.ui.sentence.var import Var
from ..interfaces.ui import PageType

if TYPE_CHECKING:
    from ..interfaces.plugin import PluginType

LIFECYCLE_MAP: dict[LifecycleHook, Callable] = {
    LifecycleHook.INSTALL: lambda self: self.plugin.on_install(),
    LifecycleHook.START: lambda self: self.plugin.on_start(),
    LifecycleHook.PAUSE: lambda self: self.plugin.on_pause(),
    LifecycleHook.RESUME: lambda self: self.plugin.on_resume(),
    LifecycleHook.DISPOSE: lambda self: self.plugin.on_dispose(),
    LifecycleHook.UNINSTALL: lambda self: self.plugin.on_uninstall(),
}


class Bridge:
    def __init__(self, plugin: PluginType, queue_size: int = 10):
        self.plugin = plugin
        self.running = True
        self.connected_clients = set()
        self.message_queue: Optional[asyncio.Queue] = None
        self.response_queue: Optional[asyncio.Queue] = None
        self.asyncio_loop: Optional[asyncio.AbstractEventLoop] = None
        self.queue_size = queue_size
        self.port = int(os.environ.get("PYRITE_IDE_PLUGIN_PORT"))  # type: ignore

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
                            self.push(err(env, ErrorCode.KEY_NOT_FOUND,
                                          f"Event '{payload.name}' not found"), websocket)
                            return
                        try:
                            event(**payload.args)
                            self.push(ok(env), websocket)
                        except Exception as e:
                            self.push(err(env, ErrorCode.INTERNAL_ERROR, str(e)), websocket)

                    case "ide.response.ok" | "ide.response.error":
                        if self.response_queue is not None:
                            try:
                                self.response_queue.put_nowait(env)
                            except asyncio.QueueFull:
                                print("Warning: Response queue was full")

                    case "ide.lifecycle.hook":
                        payload = LifecyclePayload(**env.payload)
                        handler = LIFECYCLE_MAP.get(payload.hook)
                        if handler:
                            try:
                                handler(self)
                                self.push(ok(env), websocket)
                            except Exception as e:
                                self.push(err(env, ErrorCode.INTERNAL_ERROR, str(e)), websocket)
                        else:
                            self.push(err(env, ErrorCode.API_NOT_FOUND,
                                          f"Unknown lifecycle hook: {payload.hook}"), websocket)

                    case "ide.response.path":
                        payload = PathResponsePayload(**env.payload)
                        if payload.path:
                            self.plugin.assets = Path(payload.path)
                            self.refresh()
                        else:
                            print("Warning: path response missing path")

                    case _:
                        self.push(err(env, ErrorCode.INVALID_REQUEST,
                                      f"Unknown message type: {env.type}"), websocket)

        except websockets.exceptions.ConnectionClosed:
            print("Connection closed")
            self.connected_clients.discard(websocket)

    async def send(self, websocket, envelope: Envelope):
        try:
            print("Sending:", envelope.type)
            await websocket.send(envelope.json())
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed")
            self.connected_clients.discard(websocket)
        except Exception as e:
            print(f"Error in send: {e}")

    async def send_all(self, envelope: Envelope):
        for client in self.connected_clients.copy():
            await self.send(client, envelope)

    def refresh(self):
        if not isinstance(self.plugin, PluginType):
            print("Warning: Cannot find plugin in Bridge")
            return
        self.plugin.on_refresh()
        if not hasattr(self.plugin, "pages"):
            print("Warning: Plugin has no pages to refresh")
            return
        if not self.plugin.pages:
            print("Warning: Plugin has empty pages to refresh")
            return
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
            print("Error in refreshing pages:", e)

    def push(self, envelope: Envelope, client=None):
        if self.asyncio_loop is None or self.message_queue is None:
            print("Error: cannot find loop")
            return

        def _put():
            assert self.message_queue is not None
            try:
                self.message_queue.put_nowait([client, envelope])
            except asyncio.QueueFull:
                print("Warning: Message queue was full")

        self.asyncio_loop.call_soon_threadsafe(_put)

    def push_wait_response(self, envelope: Envelope,
                           callback: Optional[Callable[[dict], Any]] = None,
                           client=None):
        self.push(envelope, client)

    def let(self, name: Var, value: Any):
        paths = list(name.paths)
        if paths and paths[0] in {"data", "args", "state"}:
            paths.pop(0)
        self.push(
            request(
                "sdk.var.set",
                VarSetPayload(
                    name=Var(*paths).to_rfw(),
                    value=value,
                ),
            )
        )

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
                print(f"Error in loop: {e}")
            finally:
                self.message_queue.task_done()
        self.server.close()
        print("Server closed")

    async def main(self):
        self.message_queue = asyncio.Queue(maxsize=self.queue_size)
        self.response_queue = asyncio.Queue(maxsize=self.queue_size)
        self.asyncio_loop = asyncio.get_running_loop()
        async with websockets.serve(self.handler, "localhost", self.port) as self.server:
            print(f"Server started on ws://localhost:{self.port}")
            await asyncio.gather(self.server.wait_closed(), self.loop())

    def start(self):
        try:
            if sys.platform == 'win32':
                asyncio.set_event_loop_policy(
                    asyncio.WindowsSelectorEventLoopPolicy()
                )
            asyncio.run(self.main())
        except KeyboardInterrupt:
            self.running = False
