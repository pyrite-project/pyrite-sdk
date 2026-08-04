import asyncio
import unittest
from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any

from pyrite_sdk.core.bridge import Bridge
from pyrite_sdk.core.transport import (
    ClientHandler,
    RawMessage,
    Transport,
    TransportClosedError,
    TransportState,
)
from pyrite_sdk.models.schema import Envelope


class FakeTransport(Transport):
    def __init__(self):
        self._state = TransportState.CLOSED
        self.incoming: dict[Any, list[RawMessage]] = {}
        self.sent: list[tuple[Any, RawMessage]] = []
        self.send_error: Exception | None = None
        self.close_effects = 0

    @property
    def state(self) -> TransportState:
        return self._state

    async def start(self, handler: ClientHandler) -> None:
        self._state = TransportState.READY

    async def _messages(self, client: Any) -> AsyncIterator[RawMessage]:
        for message in self.incoming.get(client, []):
            yield message

    def messages(self, client: Any) -> AsyncIterator[RawMessage]:
        return self._messages(client)

    async def send(self, client: Any, message: RawMessage) -> None:
        if self.send_error is not None:
            raise self.send_error
        self.sent.append((client, message))

    async def wait_closed(self) -> None:
        return

    def close(self) -> None:
        if self._state == TransportState.CLOSED:
            return
        self.close_effects += 1
        self._state = TransportState.CLOSED


class TransportTest(unittest.TestCase):
    def test_bridge_dispatches_through_opaque_fake_transport(self):
        transport = FakeTransport()
        bridge = Bridge(SimpleNamespace(pages={}), transport=transport)
        client = object()
        transport.incoming[client] = [
            Envelope(
                type="ide.initialize",
                payload={
                    "protocolVersion": 1,
                    "pluginId": "standalone",
                    "capabilities": ["sdk.v1"],
                },
            ).model_dump_json(by_alias=True)
        ]

        asyncio.run(bridge.handler(client))

        self.assertEqual(len(transport.sent), 1)
        response = Envelope.model_validate_json(transport.sent[0][1])
        self.assertEqual(response.type, "sdk.initialize")
        self.assertNotIn(client, bridge.connected_clients)

    def test_transport_closed_error_is_absorbed_by_bridge_lifecycle(self):
        transport = FakeTransport()
        bridge = Bridge(SimpleNamespace(pages={}), transport=transport)
        client = object()
        bridge.connected_clients.add(client)
        transport.send_error = TransportClosedError("closed")

        asyncio.run(
            bridge.send(client, Envelope(type="sdk.fixture", payload={}))
        )

        self.assertNotIn(client, bridge.connected_clients)

    def test_close_is_idempotent(self):
        transport = FakeTransport()
        asyncio.run(transport.start(lambda client: asyncio.sleep(0)))

        transport.close()
        transport.close()

        self.assertEqual(transport.state, TransportState.CLOSED)
        self.assertEqual(transport.close_effects, 1)


if __name__ == "__main__":
    unittest.main()
