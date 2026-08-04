import asyncio
import json
import unittest
from pathlib import Path
from types import SimpleNamespace

from pyrite_sdk.models.schema import Envelope, request
from tests.fakes import FakeClient, make_bridge


V1_FIXTURE = (
    Path(__file__).parent / "fixtures" / "protocol" / "protocol_v1_handshake.json"
)


class ProtocolFixtureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(V1_FIXTURE.read_text(encoding="utf-8"))

    def test_v1_handshake_and_requests_match_envelope_model(self):
        for name in ("ideInitialize", "sdkInitialize", "ideInitialized", "sdkReady"):
            envelope = Envelope.model_validate(self.fixture[name])
            self.assertEqual(
                envelope.model_dump(by_alias=True, mode="json"),
                self.fixture[name],
            )

        timed_request = Envelope.model_validate(self.fixture["ideTimedRequest"])
        cancellation = Envelope.model_validate(self.fixture["ideRequestCancel"])
        self.assertEqual(timed_request.deadline, 1700000005104)
        self.assertEqual(cancellation.payload["requestId"], timed_request.request_id)

        generated = request(
            "sdk.settings.get",
            payload={"name": "editor.font_size"},
        )
        self.assertEqual(generated.protocol_version, 1)
        self.assertEqual(generated.payload, {"name": "editor.font_size"})

    def test_business_message_before_handshake_returns_protocol_error(self):
        bridge = make_bridge(SimpleNamespace())
        bridge._handshake_state = "pending"
        message = dict(self.fixture["ideInitialize"])
        message.update(
            {
                "pluginId": "standalone",
                "sessionId": "standalone",
                "generation": 1,
                "type": "ide.command.execute",
                "payload": {
                    "commandId": "fixture.command",
                    "args": {},
                    "context": {},
                },
            }
        )
        client = FakeClient([json.dumps(message)])

        asyncio.run(bridge.handler(client))

        response = Envelope.model_validate_json(client.sent[-1])
        self.assertEqual(response.type, "sdk.response.error")
        self.assertEqual(response.payload["code"], "protocol_error")

    def test_response_fixture_routes_to_pending_callback(self):
        callback_data = []
        bridge = make_bridge(SimpleNamespace())
        bridge.callbacks["fixture-request-1"] = lambda **data: callback_data.append(
            data
        )
        bridge._pending_responses = 1
        response = dict(self.fixture["sdkReady"])
        response.update(
            {
                "pluginId": "standalone",
                "sessionId": "standalone",
                "generation": 1,
                "requestId": "fixture-response-1",
                "replyTo": "fixture-request-1",
                "type": "sdk.response.ok",
                "sequence": 1,
                "payload": {"data": {"name": "editor.font_size", "value": 14.0}},
            }
        )

        asyncio.run(bridge.handler(FakeClient([json.dumps(response)])))

        self.assertEqual(
            callback_data,
            [{"data": {"name": "editor.font_size", "value": 14.0}}],
        )
        self.assertEqual(bridge._pending_responses, 0)

    def test_expired_request_is_rejected_before_dispatch(self):
        bridge = make_bridge(SimpleNamespace())
        pushed = []
        bridge.push = lambda envelope, client=None: pushed.append(envelope)
        message = dict(self.fixture["ideTimedRequest"])
        message.update(
            {
                "pluginId": "standalone",
                "sessionId": "standalone",
                "generation": 1,
                "sequence": 1,
                "deadline": 1,
            }
        )

        asyncio.run(bridge.handler(FakeClient([json.dumps(message)])))

        self.assertEqual(pushed[-1].type, "ide.response.error")
        self.assertEqual(pushed[-1].payload["code"], "timeout")


if __name__ == "__main__":
    unittest.main()
