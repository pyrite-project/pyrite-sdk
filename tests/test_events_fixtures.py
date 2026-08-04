import asyncio
import json
import unittest
from pathlib import Path
from types import SimpleNamespace

from pyrite_sdk.api.events import PluginEventBus
from pyrite_sdk.models.schema import Envelope
from tests.fakes import FakeClient, make_bridge


FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "protocol"
    / "protocol_v1_events.json"
)


class EventsFixtureTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_event_fixtures_round_trip_through_envelope(self):
        for name in (
            "sdkEventsSubscribe",
            "sdkEventsSubscribeResponse",
            "ideEventEmit",
            "sdkEventsUnsubscribe",
        ):
            envelope = Envelope.model_validate(self.fixture[name])
            self.assertEqual(
                envelope.model_dump(by_alias=True, mode="json"),
                self.fixture[name],
            )

    async def test_emit_fixture_dispatches_to_event_handler(self):
        received = []
        plugin = SimpleNamespace(pages={})
        bridge = make_bridge(plugin)
        # A plugin subscribes from inside the running event loop, so wire the
        # bridge's loop/queue the way main() would before pushing requests.
        bridge.asyncio_loop = asyncio.get_running_loop()
        bridge.message_queue = asyncio.Queue(maxsize=50)
        plugin.events = PluginEventBus(bridge)

        subscription = plugin.events.subscribe(
            "editor.document.changed", lambda event: received.append(event)
        )
        # Rewrite the fixture emit to target the live subscription id and the
        # active standalone session.
        emit = dict(self.fixture["ideEventEmit"])
        emit.update(
            {
                "pluginId": "standalone",
                "sessionId": "standalone",
                "generation": 1,
                "sequence": 1,
            }
        )
        emit["payload"] = dict(emit["payload"])
        emit["payload"]["subscriptionId"] = subscription.id

        await bridge.handler(FakeClient([json.dumps(emit)]))

        self.assertEqual(received, [{"documentId": "doc-7", "revision": 18}])


if __name__ == "__main__":
    unittest.main()
