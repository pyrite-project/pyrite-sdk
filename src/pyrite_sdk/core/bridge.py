import asyncio
import websockets
import os
from ..models.consts import *
from ..models.schema import *
from ..models.plugin import Plugin
from ..api.ui.page import Page

class Bridge:
    def __init__(self, plugin: Plugin, queue_size: int = 10):
        self.plugin = plugin
        self.running = True
        self.connected_clients = set()
        self.message_queue = None
        self.asyncio_loop = None
        self.queue_size = queue_size
        self.port = int(os.environ.get("PYRITE_IDE_PLUGIN_PORT")) # type: ignore

    async def handler(self, websocket):
        self.connected_clients.add(websocket)
        try:
            async for message in websocket:
                message = Message.parse_raw(message)
                print("Received message:", message)
                match message.cmd:
                    case MessageCommands.GET_PAGES:
                        try:
                            self.push(
                                message = Message(
                                    cmd = MessageCommands.RESPONSE,
                                    data = MessageData(
                                        pages = {name:page.to_rfw() for name, page in self.plugin.pages.items()},
                                    ),
                                    source = message
                                )
                            )
                        except Exception as e:
                            print("Error in sending pages")
                    case MessageCommands.EVENT_CALLBACK:
                        assert message.data.page is not None
                        _page: Optional[Page] = self.plugin.pages.get(message.data.page)
                        assert _page is not None
                        page: Page = _page
                        if not page:
                            self.send_error(websocket, Error.KEY_NOT_FOUND, message)
                            return
                        assert message.data.callback is not None
                        callback: CallbackData = message.data.callback
                        event = page.events.get(callback.event)
                        if not event:
                            await self.send_error(websocket, Error.KEY_NOT_FOUND, message)
                            return
                        try:
                            event(**callback.args)
                        except Exception as e:
                            print(f"Error in callback {event}: {e}")
                    case MessageCommands.RESPONSE:
                        await self.response_queue.put(message)
                    case MessageCommands.LIFECYCLE_HOOKS:
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
                            await self.send_error(websocket, Error.API_NOT_FOUND, message)
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed")
            self.connected_clients.remove(websocket)

    async def send(self, websocket, message: Message):
        try:
            print("Sending response:", message)
            await websocket.send(message.json())
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed")
            self.connected_clients.remove(websocket)
        except Exception as e:
            print(f"Error in send: {e}")

    async def send_all(self, message: Message):
        for client in self.connected_clients.copy():
            await self.send(client, message)

    async def send_error(self, websocket, error, source):
        self.push(
            Message(
                cmd = MessageCommands.ERROR_RESPONSE,
                data = MessageData(err = error),
                source = source
            ),
            websocket
        )

    def push(self, message, client=None):
        if self.asyncio_loop is None or self.message_queue is None:
            print("Error: cannot find loop")
            return

        def _put():
            assert self.message_queue is not None
            try:
                self.message_queue.put_nowait([client, message])
            except asyncio.QueueFull:
                print("Warning: Queue was full")

        self.asyncio_loop.call_soon_threadsafe(_put)

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

    def start(self):
        try:
            asyncio.run(self.main())
        except KeyboardInterrupt:
            self.running = False

