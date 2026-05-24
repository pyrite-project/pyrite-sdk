import asyncio
import websockets
import os
import sys
from pathlib import Path
from typing import Optional
from copy import copy
from ..models.consts import *
from ..models.schema import *
from ..models.plugin import Plugin
from ..api.ui.sentence.var import Var
from ..interfaces.ui import PageType

class Bridge:
    def __init__(self, plugin: Optional[Plugin] = None, queue_size: int = 10):
        self.plugin = plugin
        self.running = True
        self.connected_clients = set()
        self.message_queue = None
        self.asyncio_loop = None
        self.queue_size = queue_size
        self.port = int(os.environ.get("PYRITE_IDE_PLUGIN_PORT")) # type: ignore

    async def handler(self, websocket):
        if self.plugin is None:
            raise RuntimeError("Bridge.start(plugin) must be called before accepting websocket connections")

        self.connected_clients.add(websocket)
        msd = MessageData(path_type=PathType.ASSETS)
        print("MSD:", msd)
        self.push(
            Message(
                cmd=MessageCommands.SDK.REQUEST.GET_PATH,
                data=msd,
            ),
            websocket,
        )
        try:
            async for message in websocket:
                message = Message.parse_raw(message)
                print("DEBUG MATCH:", repr(message.cmd), type(message.cmd).__name__, type(message.cmd).__module__)
                print("Received message:", message)
                match message.cmd:
                    case MessageCommands.IDE.REQUEST.REFRESH:
                        self.refresh()
                    case MessageCommands.IDE.REQUEST.EVENT_CALLBACK:
                        assert message.data.page is not None
                        _page: Optional[PageType] = self.plugin.pages.get(message.data.page)
                        assert _page is not None
                        page: PageType = _page
                        if not page:
                            self.send_error(websocket, Error.KEY_NOT_FOUND, message)
                            return
                        assert message.data.callback is not None
                        callback: CallbackData = message.data.callback
                        event = page.events.get(callback.event)
                        if not event:
                            self.send_error(websocket, Error.KEY_NOT_FOUND, message)
                            return
                        try:
                            event(**callback.args)
                        except Exception as e:
                            print(f"Error in callback {event}: {e}")
                    case MessageCommands.IDE.RESPONSE.RESPONSE:
                        assert self.response_queue is not None
                        try:
                            self.response_queue.put_nowait(message)
                        except asyncio.QueueFull:
                            print("Warning: Response queue was full")
                    case MessageCommands.IDE.REQUEST.LIFECYCLE_HOOKS:
                        try:
                            match message.data.lifecycle_hook:
                                case LifecycleHooks.ON_INSTALL:
                                    self.plugin.on_install()
                                case LifecycleHooks.ON_START:
                                    self.plugin.on_start()
                                case LifecycleHooks.ON_PAUSE:
                                    self.plugin.on_pause()
                                case LifecycleHooks.ON_RESUME:
                                    self.plugin.on_resume()
                                case LifecycleHooks.ON_DISPOSE:
                                    self.plugin.on_dispose()
                                case LifecycleHooks.ON_UNINSTALL:
                                    self.plugin.on_uninstall()
                        except AttributeError:
                            print(f"Cannot find api {message.data.lifecycle_hook}")
                            self.send_error(websocket, Error.API_NOT_FOUND, message)
                    case MessageCommands.IDE.RESPONSE.GET_PATH:
                        if message.data.path is not None:
                            self.plugin.assets = Path(message.data.path)
                            self.refresh()
                        else:
                            print("Warning: GET_PATH message missing path")
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed")
            self.connected_clients.remove(websocket)

    async def send(self, websocket, message: Message):
        try:
            print("Sending response:", message)
            await websocket.send(message.json(by_alias=True))
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed")
            self.connected_clients.remove(websocket)
        except Exception as e:
            print(f"Error in send: {e}")

    async def send_all(self, message: Message):
        for client in self.connected_clients.copy():
            await self.send(client, message)

    def send_error(self, websocket, error, source):
        self.push(
            Message(
                cmd = MessageCommands.SDK.RESPONSE.ERROR_RESPONSE,
                data = MessageData(err = error),
                source = source
            ),
            websocket
        )

    def refresh(self):
        self.plugin.on_refresh()
        if not hasattr(self.plugin, "pages"):
            print("Warning: Plugin has no pages to refresh")
            return
        if not self.plugin.pages:
            print("Warning: Plugin has empty pages to refresh")
            return
        try:
            self.push(
                message = Message(
                    cmd = MessageCommands.SDK.REQUEST.REFRESH,
                    data = MessageData(
                        pages = {name:page.to_rfw() for name, page in self.plugin.pages.items()},
                    ),
                    source = None
                )
            )
        except Exception as e:
            print("Error in refreshing pages:", e)

    def push(self, message, client=None):
        if self.asyncio_loop is None or self.message_queue is None:
            print("Error: cannot find loop")
            return

        def _put():
            assert self.message_queue is not None
            try:
                self.message_queue.put_nowait([client, message])
            except asyncio.QueueFull:
                print("Warning: Message queue was full")

        self.asyncio_loop.call_soon_threadsafe(_put)

    def let(self, name: Var, value: Any):
        paths = list(name.paths)
        if paths and paths[0] in {"data", "args", "state"}:
            paths.pop(0)
        print("INBRIDGE.LET", paths, name.paths, value, Var(*paths).to_rfw())
        self.push(
            Message(
                cmd = MessageCommands.SDK.REQUEST.SET_VAR,
                data = MessageData(var_name = Var(*paths).to_rfw(), var_value = value),
                source = None
            )
        )

    async def loop(self):
        while self.running:
            assert self.message_queue is not None
            client, message = await self.message_queue.get()
            try:
                if client:
                    await self.send(client, message)
                else:
                    await self.send_all(message)
            except Exception as e:
                print(f"Error in loop: {e}")
            finally:
                self.message_queue.task_done()
        self.server.close()
        print("Sever closed")

    async def main(self):
        self.message_queue = asyncio.Queue(maxsize = self.queue_size)
        self.response_queue = asyncio.Queue(maxsize = self.queue_size)
        self.asyncio_loop = asyncio.get_running_loop()
        async with websockets.serve(self.handler, "localhost", self.port) as self.server:
            print(f"Server started on ws://localhost:{self.port}")
            await asyncio.gather(self.server.wait_closed(), self.loop())

    def start(self, plugin: Plugin):
        self.plugin = plugin
        try:
            if sys.platform == 'win32':
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            asyncio.run(self.main())
        except KeyboardInterrupt:
            self.running = False

