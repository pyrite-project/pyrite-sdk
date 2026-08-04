import unittest

from pyrite_sdk.api.events import PluginEventBus
from pyrite_sdk.api.runtime import (
    ObjectInfo,
    Runtime,
    RuntimeSession,
    RuntimeUnavailableError,
    StaleReferenceError,
    Variable,
)


class FakeBridge:
    def __init__(self):
        self.calls = []

    def push_wait_response(self, envelope, callback=None, client=None):
        self.calls.append((envelope, callback, client))


class FakeError:
    def __init__(self, code, message="err"):
        self.code = code
        self.message = message


class RuntimeModelTest(unittest.TestCase):
    def test_variable_from_json_matches_data_model(self):
        var = Variable.from_json(
            {
                "name": "items",
                "type": "list",
                "repr": "[1, 2, 3]",
                "reference": "runtime-1:generation-4:obj-42",
                "hasChildren": True,
                "namedVariables": 0,
                "indexedVariables": 3,
            }
        )
        self.assertEqual(var.name, "items")
        self.assertEqual(var.type, "list")
        self.assertEqual(var.reference, "runtime-1:generation-4:obj-42")
        self.assertTrue(var.has_children)
        self.assertEqual(var.indexed_variables, 3)

    def test_session_from_json(self):
        session = RuntimeSession.from_json(
            {
                "sessionId": "device",
                "generation": 4,
                "capability": "unavailable",
                "programState": "running",
            }
        )
        self.assertEqual(session.session_id, "device")
        self.assertEqual(session.generation, 4)
        self.assertEqual(session.capability, "unavailable")
        self.assertEqual(session.program_state, "running")

    def test_object_info_parses_attributes(self):
        info = ObjectInfo.from_json(
            {
                "reference": "r1",
                "type": "dict",
                "repr": "{...}",
                "attributes": [{"name": "a", "type": "int", "repr": "1"}],
            }
        )
        self.assertEqual(info.attributes[0].name, "a")


class RuntimeApiTest(unittest.TestCase):
    def setUp(self):
        self.bridge = FakeBridge()
        self.events = PluginEventBus(self.bridge)
        self.runtime = Runtime(self.bridge, self.events)

    def last(self):
        envelope, callback, _ = self.bridge.calls[-1]
        return envelope, callback

    def test_sessions_command(self):
        self.runtime.sessions()
        envelope, _ = self.last()
        self.assertEqual(envelope.type, "sdk.runtime.sessions")

    def test_children_sends_reference_and_paging(self):
        self.runtime.children("ref-1", start=10, count=20)
        envelope, _ = self.last()
        self.assertEqual(envelope.type, "sdk.runtime.children")
        self.assertEqual(
            envelope.payload, {"reference": "ref-1", "start": 10, "count": 20}
        )

    def test_children_parses_paged_result(self):
        received = {}
        self.runtime.children("ref-1", callback=lambda page=None, **_: received.update(p=page))
        _, callback = self.last()
        callback(
            data={
                "items": [{"name": "0", "type": "int", "repr": "1"}],
                "total": 3,
                "start": 0,
            }
        )
        page = received["p"]
        self.assertEqual(page.total, 3)
        self.assertEqual(page.items[0].name, "0")

    def test_stale_reference_maps_to_exception(self):
        received = {}
        self.runtime.children("ref-1", callback=lambda error=None, **_: received.update(e=error))
        _, callback = self.last()
        callback(error=FakeError("stale_reference"))
        self.assertIsInstance(received["e"], StaleReferenceError)

    def test_unavailable_maps_to_exception(self):
        received = {}
        self.runtime.scopes("device", callback=lambda error=None, **_: received.update(e=error))
        _, callback = self.last()
        callback(error=FakeError("unavailable"))
        self.assertIsInstance(received["e"], RuntimeUnavailableError)

    def test_variables_sends_scope_and_paging(self):
        self.runtime.variables("device", "globals", start=0, count=50)
        envelope, _ = self.last()
        self.assertEqual(envelope.type, "sdk.runtime.variables")
        self.assertEqual(
            envelope.payload,
            {"sessionId": "device", "scopeId": "globals", "start": 0, "count": 50},
        )

    def test_on_variables_changed_subscribes(self):
        self.runtime.on_variables_changed(lambda event: None)
        envelope, _ = self.last()
        self.assertEqual(envelope.type, "sdk.events.subscribe")
        self.assertEqual(envelope.payload["topic"], "runtime.variables.changed")

    def test_on_backend_restarted_subscribes(self):
        self.runtime.on_backend_restarted(lambda event: None)
        envelope, _ = self.last()
        self.assertEqual(envelope.payload["topic"], "runtime.backend.restarted")


if __name__ == "__main__":
    unittest.main()
