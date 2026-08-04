from collections.abc import AsyncIterator
from typing import Any

from pyrite_sdk.core.bridge import Bridge
from pyrite_sdk.core.transport import (
    ClientHandler,
    RawMessage,
    Transport,
    TransportState,
)


class FakeClient:
    def __init__(self, messages=()):
        self._messages = iter(messages)
        self.sent = []

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._messages)
        except StopIteration as error:
            raise StopAsyncIteration from error

    async def send(self, message):
        self.sent.append(message)


class ClientTransport(Transport):
    def __init__(self):
        self._state = TransportState.CLOSED

    @property
    def state(self) -> TransportState:
        return self._state

    async def start(self, handler: ClientHandler) -> None:
        self._state = TransportState.READY

    def messages(self, client: Any) -> AsyncIterator[RawMessage]:
        return client

    async def send(self, client: Any, message: RawMessage) -> None:
        await client.send(message)

    async def wait_closed(self) -> None:
        return

    def close(self) -> None:
        self._state = TransportState.CLOSED


def make_bridge(plugin, *, handshake_ready: bool = True) -> Bridge:
    bridge = Bridge(plugin, transport=ClientTransport())
    if handshake_ready:
        bridge._handshake_state = "ready"
    return bridge
