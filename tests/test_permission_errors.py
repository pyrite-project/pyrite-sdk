import asyncio
import unittest
from types import SimpleNamespace

from pyrite_sdk.core.errors import (
    PermissionDeniedError,
    UnknownCommandError,
)
from pyrite_sdk.models.schema import Envelope
from tests.fakes import FakeClient, make_bridge


class PermissionErrorTest(unittest.TestCase):
    def make_bridge(self):
        return make_bridge(SimpleNamespace(pages={}))

    def dispatch_error(self, code, details=None):
        bridge = self.make_bridge()
        received = []
        bridge.callbacks["request-1"] = lambda **data: received.append(data)
        bridge._pending_responses = 1
        envelope = Envelope(
            type="sdk.response.error",
            request_id="response-1",
            reply_to="request-1",
            payload={
                "code": code,
                "message": "request rejected",
                "details": details,
            },
        )

        asyncio.run(
            bridge.handler(
                FakeClient([envelope.model_dump_json(by_alias=True)])
            )
        )
        return received[0]["error"]

    def test_permission_denial_uses_dedicated_exception(self):
        error = self.dispatch_error(
            "permission_denied",
            {"required": "settings:write"},
        )

        self.assertIsInstance(error, PermissionDeniedError)
        self.assertEqual(error.code, "permission_denied")
        self.assertEqual(error.required_permission, "settings:write")

    def test_unknown_command_is_not_reported_as_network_error(self):
        error = self.dispatch_error("unknown_command")

        self.assertIsInstance(error, UnknownCommandError)
        self.assertEqual(error.code, "unknown_command")


if __name__ == "__main__":
    unittest.main()
