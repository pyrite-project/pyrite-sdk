import json
import unittest
from pathlib import Path

from pyrite_sdk.api.document import Document, SymbolResult
from pyrite_sdk.models.schema import Envelope


FIXTURE = (
    Path(__file__).parent
    / "fixtures"
    / "protocol"
    / "protocol_v1_editor_document.json"
)


class DocumentFixtureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_fixtures_round_trip_through_envelope(self):
        for name in (
            "sdkActiveDocumentGet",
            "sdkDocumentSymbols",
            "sdkDocumentSymbolsResponse",
            "sdkDocumentReveal",
            "ideActiveDocumentChanged",
            "ideDocumentChanged",
        ):
            envelope = Envelope.model_validate(self.fixture[name])
            self.assertEqual(
                envelope.model_dump(by_alias=True, mode="json"),
                self.fixture[name],
            )

    def test_symbol_result_parses_from_response_fixture(self):
        data = self.fixture["sdkDocumentSymbolsResponse"]["payload"]["data"]
        result = SymbolResult.from_json(data)
        self.assertEqual(result.revision, 18)
        self.assertFalse(result.stale)
        self.assertEqual(result.symbols[0].name, "Widget")
        self.assertEqual(result.symbols[0].children[0].name, "build")

    def test_active_changed_event_payload_parses_to_document(self):
        events = self.fixture["ideActiveDocumentChanged"]["payload"]["events"]
        doc = Document.from_json(events[0])
        self.assertEqual(doc.document_id, "doc-7")
        self.assertEqual(doc.file_path, "/proj/main.py")
        self.assertEqual(doc.language_id, "python")
        self.assertEqual(doc.revision, 18)

    def test_document_changed_event_carries_incremental_changes(self):
        events = self.fixture["ideDocumentChanged"]["payload"]["events"]
        self.assertEqual(events[0]["changes"], [{"start": 120, "end": 128}])
        self.assertNotIn("text", events[0])


if __name__ == "__main__":
    unittest.main()
