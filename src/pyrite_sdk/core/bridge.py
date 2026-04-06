import asyncio
import websockets
from ..models.consts import *
from ..models.schema import *

def button_clicked(args):
    print(f"(from callback func) button clicked (ARGS: {args})")

class Bridge:
    def __init__(self, pages: dict, queue_size: int = 10):
        self.pages = pages
        self.running = True
        self.connected_clients = set()
        self.message_queqe = None
        self.asyncio_loop = None
        self.queue_size = queue_size

    async def get_value(self, websocket, key, dict_, source=None):
        if key not in dict_.keys():
            error_response = Message(cmd=MessageCommands.ERROR_RESPONSE, data=MessageData(err=Error.KEY_NOT_FOUND), source=source)
            await self.push(error_response, websocket)
            return None
        return dict_.get(key, None)

    async def handler(self, websocket):
        self.connected_clients.add(websocket)
        try:
            async for message in websocket:
                message = Message.model_validate_json(message)
                print("Received message:", message)
                cmd = message.cmd
                if cmd == MessageCommands.GET_REGISTER:
                    self.push(
                        message = Message(
                            cmd = MessageCommands.RESPONSE,
                            data = MessageData(
                                pages = {name:page.to_rfw() for name, page in self.pages.items()},
                            ),
                            source = message
                        )
                    )
                elif cmd == MessageCommands.EVENT_CALLBACK:
                    page = await self.get_value(websocket, message.data.page, self.pages, source=message)
                    if not page:
                        return
                    callback = message.data.callback
                    event = await self.get_value(websocket, callback.event, page.events, source=message)
                    if not event:
                        return
                    try:
                        event(**callback.args)
                    except Exception as e:
                        print(f"Error in callback {event}: {e}")
                elif cmd == MessageCommands.RESPONSE:
                    self.response_queue.put(message)
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed")
            self.connected_clients.remove(websocket)

    async def send(self, websocket, message: Message):
        try:
            print("Sending response:", message)
            await websocket.send(message.model_dump_json())
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed")
            self.connected_clients.remove(websocket)
        except Exception as e:
            print(f"Error in send: {e}")

    async def send_all(self, message: Message):
        for client in self.connected_clients.copy():
            await self.send(client, message)

    async def loop(self):
        while self.running:
            client, message = await self.message_queqe.get()
            try:
                if client:
                    await self.send(client, message)
                else:
                    await self.send_all(message)
            except Exception as e:
                print(f"Error in loop: {e}")
            finally:
                self.message_queqe.task_done()
        self.server.close()
        print("Sever closed")

    async def main(self):
        self.message_queqe = asyncio.Queue(maxsize = self.queue_size)
        self.response_queue = asyncio.Queue(maxsize = self.queue_size)
        self.asyncio_loop = asyncio.get_running_loop()
        async with websockets.serve(self.handler, "localhost", 8765) as self.server:
            print("Server started on ws://localhost:8765")
            await asyncio.gather(self.server.wait_closed(), self.loop())

    def start(self):
        try:
            asyncio.run(self.main())
        except KeyboardInterrupt:
            self.running = False

    def push(self, message, client=None):
        if self.asyncio_loop is None or self.message_queqe is None:
            print("Error: cannot find loop")
            return

        def _put():
            try:
                self.message_queqe.put_nowait([client, message])
            except asyncio.QueueFull:
                print("Warning: Queue was full")

        self.asyncio_loop.call_soon_threadsafe(_put)
