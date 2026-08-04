import json
import unittest
from pathlib import Path

from pyrite_sdk.api.view import ViewModel, Views
from pyrite_sdk.models.schema import Envelope


FIXTURE = Path(__file__).parent / "fixtures" / "protocol" / "protocol_v1_view.json"


class FakeBridge:
    def __init__(self):
        self.calls = []

    def push_wait_response(self, envelope, callback=None, client=None):
        self.calls.append((envelope, callback, client))

    def types(self):
        return [e.type for e, _, _ in self.calls]


class ViewFixtureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_fixtures_round_trip_through_envelope(self):
        for name in (
            "sdkViewSnapshot",
            "sdkViewPatch",
            "ideViewAck",
            "ideViewNack",
            "ideViewResync",
            "ideViewVisibilityChanged",
        ):
            envelope = Envelope.model_validate(self.fixture[name])
            self.assertEqual(
                envelope.model_dump(by_alias=True, mode="json"),
                self.fixture[name],
            )

    def test_sdk_produces_the_fixture_patch_shape(self):
        bridge = FakeBridge()
        model = ViewModel(bridge, "outline", instance_id="inst-1")
        snapshot = self.fixture["sdkViewSnapshot"]["payload"]
        model.snapshot(snapshot["nodes"], revision=snapshot["revision"])

        expected = self.fixture["sdkViewPatch"]["payload"]
        with model.batch():
            model.insert("n3", {"label": "dispose"}, index=2)
            model.update("n1", {"label": "Widget2"})
            model.move("n3", 0)
            model.remove("n2")

        patch = [e for e, _, _ in bridge.calls if e.type == "sdk.view.patch"][0]
        self.assertEqual(patch.payload["baseRevision"], expected["baseRevision"])
        self.assertEqual(patch.payload["revision"], expected["revision"])
        self.assertEqual(patch.payload["ops"], expected["ops"])

    def test_ack_fixture_advances_the_local_revision(self):
        bridge = FakeBridge()
        views = Views(bridge)
        model = views.create("outline", instance_id="inst-1")
        model.snapshot([{"id": "n1"}])
        model.insert("n3", {})
        ack = self.fixture["ideViewAck"]
        views.handle_frame(ack["type"], ack["payload"])
        self.assertEqual(model.revision, 2)
        self.assertFalse(model.has_in_flight)

    def test_nack_fixture_triggers_a_snapshot(self):
        bridge = FakeBridge()
        views = Views(bridge)
        model = views.create("outline", instance_id="inst-1")
        model.snapshot([{"id": "n1"}])
        model.insert("n3", {})
        bridge.calls.clear()
        nack = self.fixture["ideViewNack"]
        views.handle_frame(nack["type"], nack["payload"])
        self.assertIn("sdk.view.snapshot", bridge.types())


if __name__ == "__main__":
    unittest.main()
