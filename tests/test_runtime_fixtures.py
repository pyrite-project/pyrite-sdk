import json
import unittest
from pathlib import Path

from pyrite_sdk.api.runtime import RuntimeSession, Variable
from pyrite_sdk.models.schema import Envelope


FIXTURE = (
    Path(__file__).parent / "fixtures" / "protocol" / "protocol_v1_runtime.json"
)


class RuntimeFixtureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_fixtures_round_trip_through_envelope(self):
        for name in (
            "sdkRuntimeVariables",
            "sdkRuntimeVariablesResponse",
            "sdkRuntimeChildren",
            "ideProgramPaused",
            "ideBackendRestarted",
        ):
            envelope = Envelope.model_validate(self.fixture[name])
            self.assertEqual(
                envelope.model_dump(by_alias=True, mode="json"),
                self.fixture[name],
            )

    def test_variables_response_parses_to_typed_variable(self):
        items = self.fixture["sdkRuntimeVariablesResponse"]["payload"]["data"][
            "items"
        ]
        var = Variable.from_json(items[0])
        self.assertEqual(var.name, "items")
        self.assertEqual(var.type, "list")
        self.assertEqual(var.reference, "runtime-device:generation-4:obj-42")
        self.assertTrue(var.has_children)
        self.assertEqual(var.indexed_variables, 3)

    def test_backend_restarted_event_bumps_generation(self):
        paused = self.fixture["ideProgramPaused"]["payload"]["events"][0]
        restarted = self.fixture["ideBackendRestarted"]["payload"]["events"][0]
        paused_session = RuntimeSession.from_json(paused)
        restarted_session = RuntimeSession.from_json(restarted)
        self.assertEqual(paused_session.program_state, "paused")
        self.assertGreater(
            restarted_session.generation, paused_session.generation
        )
        self.assertEqual(restarted_session.program_state, "idle")


if __name__ == "__main__":
    unittest.main()
