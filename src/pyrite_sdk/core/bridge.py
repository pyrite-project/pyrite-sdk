import asyncio
from websockets.asyncio.server import serve
from ..models.consts import *
from ..models.schema import *

def button_clicked(args):
    print(f"(from callback func) button clicked (ARGS: {args})")

class Bridge:
    def __init__(self, managers):
        self.managers = managers

    async def get_value(self, websocket, key, dict_, source=None):
        if key not in dict_.keys():
            error_response = Message(cmd=MessageCommands.ERROR_RESPONSE, data=MessageData(err=Error.KEY_NOT_FOUND), source=source)
            await self.send(websocket, error_response)
            return None
        return dict_.get(key, None)

    async def listen(self, websocket):
        async for message in websocket:
            message = Message.model_validate_json(message)
            print("Received message:", message)
            cmd = message.cmd
            if cmd == MessageCommands.GET_RFW_CODE:
                manager = await self.get_value(websocket, message.data.manager, self.managers, source=message)
                if not manager:
                    return
                manager_response = Message(cmd=MessageCommands.RESPONSE, data=MessageData(manager=manager.to_rfw()), source=message)
                await self.send(websocket, manager_response)
            elif cmd == MessageCommands.EVENT_CALLBACK:
                manager = await self.get_value(websocket, message.data.manager, self.managers, source=message)
                if not manager:
                    return
                callback = message.data.callback
                event = await self.get_value(websocket, callback.event, manager.events, source=message)
                if not event:
                    return
                event(**callback.args)

    async def send(self, websocket, response: Message):
        print("Sending response:", response)
        await websocket.send(response.model_dump_json())

    # async def send(self, websocket, cmd, data='', source=''):
    #     await websocket.send(json.dumps({"cmd": cmd, "data": data, 'source': source}))

    async def main(self):
        async with serve(self.listen, "localhost", 8765) as server:
            await server.serve_forever()

    def start(self):
        asyncio.run(self.main())
