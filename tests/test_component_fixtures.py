import json
import unittest
from pathlib import Path

from pyrite_sdk.api.components import (
    COMPONENT_SCHEMA_VERSION,
    Badge,
    Column,
    Flex,
    IconButton,
    TextField,
    Toolbar,
    VirtualList,
    ListItem,
)
from pyrite_sdk.api.view import Views
from pyrite_sdk.api.icons import Icons
from pyrite_sdk.models.schema import Envelope


FIXTURE = (
    Path(__file__).parent / "fixtures" / "protocol" / "protocol_v1_components.json"
)


class FakeBridge:
    def __init__(self):
        self.calls = []

    def push_wait_response(self, envelope, callback=None, client=None):
        self.calls.append(envelope)


class ComponentFixtureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_schema_version_matches(self):
        self.assertEqual(self.fixture["schemaVersion"], COMPONENT_SCHEMA_VERSION)

    def test_builders_reproduce_the_acceptance_page_exactly(self):
        """The SDK must emit byte-identical structure to what the IDE validates."""
        page = Column(
            Toolbar(
                IconButton(
                    id="refresh",
                    icon=Icons.refresh,
                    tooltip="Refresh",
                    on_press=lambda payload: None,
                ),
                Badge("2 results", tone="info"),
                dense=True,
            ),
            TextField(
                id="search",
                placeholder="Search symbols",
                on_change=lambda payload: None,
                on_submit=lambda payload: None,
            ),
            Flex(
                VirtualList(
                    id="results",
                    items=[
                        ListItem(id="w", label="Widget", icon=Icons.code),
                        ListItem(id="b", label="build", icon=Icons.code),
                    ],
                    selected_id="w",
                    empty_label="No matches",
                    on_select=lambda payload: None,
                    on_activate=lambda payload: None,
                ),
                direction="vertical",
            ),
            gap=4,
        )
        self.assertEqual(page.to_json(), self.fixture["acceptancePage"])

    def test_event_envelope_round_trips(self):
        envelope = Envelope.model_validate(self.fixture["ideViewEvent"])
        self.assertEqual(
            envelope.model_dump(by_alias=True, mode="json"),
            self.fixture["ideViewEvent"],
        )

    def test_component_invoke_envelope_round_trips(self):
        envelope = Envelope.model_validate(self.fixture["sdkComponentInvoke"])
        self.assertEqual(
            envelope.model_dump(by_alias=True, mode="json"),
            self.fixture["sdkComponentInvoke"],
        )

    def test_event_fixture_dispatches_to_the_matching_handler(self):
        bridge = FakeBridge()
        views = Views(bridge)
        model = views.create("outline", instance_id="inst-1")
        received = []
        model.snapshot(
            [
                VirtualList(
                    id="results",
                    items=[ListItem(id="b", label="build")],
                    on_select=received.append,
                )
            ]
        )
        frame = self.fixture["ideViewEvent"]
        views.handle_frame(frame["type"], frame["payload"])
        self.assertEqual(received[0].id, "b")

    def test_invalid_tree_cases_are_documented_for_both_sides(self):
        # The IDE asserts each of these is rejected; here we just guard the
        # fixture's shape so the two suites cannot drift apart silently.
        cases = self.fixture["invalidTrees"]
        self.assertGreater(len(cases), 0)
        for case in cases:
            self.assertIn("why", case)
            self.assertIn("node", case)
            self.assertIn("expectedPath", case)
            self.assertIn("expectedMessage", case)
            self.assertIn("type", case["node"])


if __name__ == "__main__":
    unittest.main()
