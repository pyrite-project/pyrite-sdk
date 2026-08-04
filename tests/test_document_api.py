import unittest

from pyrite_sdk.api.document import (
    Document,
    DocumentSymbol,
    EditorDocuments,
    Selection,
    SymbolResult,
)
from pyrite_sdk.api.events import PluginEventBus


class FakeBridge:
    def __init__(self):
        self.calls = []

    def push_wait_response(self, envelope, callback=None, client=None):
        self.calls.append((envelope, callback, client))


class DocumentModelTest(unittest.TestCase):
    def test_document_from_json_maps_camelcase(self):
        doc = Document.from_json(
            {
                "documentId": "d1",
                "filePath": "/a.py",
                "languageId": "python",
                "revision": 3,
                "isActive": True,
                "lineCount": 10,
                "text": "print(1)",
            }
        )
        self.assertEqual(doc.document_id, "d1")
        self.assertEqual(doc.file_path, "/a.py")
        self.assertEqual(doc.language_id, "python")
        self.assertEqual(doc.revision, 3)
        self.assertTrue(doc.is_active)
        self.assertEqual(doc.line_count, 10)

    def test_selection_parses_cursor(self):
        sel = Selection.from_json(
            {
                "documentId": "d1",
                "start": 2,
                "end": 9,
                "cursor": {"line": 1, "column": 4},
            }
        )
        self.assertEqual(sel.start, 2)
        self.assertEqual(sel.end, 9)
        self.assertEqual(sel.cursor.line, 1)
        self.assertEqual(sel.cursor.column, 4)

    def test_symbol_result_handles_hierarchical_symbols(self):
        result = SymbolResult.from_json(
            {
                "documentId": "d1",
                "revision": 7,
                "stale": False,
                "symbols": [
                    {
                        "name": "Klass",
                        "kind": 5,
                        "children": [{"name": "method", "kind": 6}],
                    }
                ],
            }
        )
        self.assertEqual(result.revision, 7)
        self.assertFalse(result.stale)
        self.assertEqual(result.symbols[0].name, "Klass")
        self.assertEqual(result.symbols[0].children[0].name, "method")

    def test_symbol_result_flags_stale(self):
        result = SymbolResult.from_json(
            {"documentId": "d1", "revision": 3, "stale": True, "symbols": []}
        )
        self.assertTrue(result.stale)


class DocumentApiTest(unittest.TestCase):
    def setUp(self):
        self.bridge = FakeBridge()
        self.events = PluginEventBus(self.bridge)
        self.docs = EditorDocuments(self.bridge, self.events)

    def last(self):
        envelope, callback, _ = self.bridge.calls[-1]
        return envelope, callback

    def test_get_active_sends_command(self):
        self.docs.get_active()
        envelope, _ = self.last()
        self.assertEqual(envelope.type, "sdk.editor.active_document.get")

    def test_get_sends_document_id(self):
        self.docs.get("d1")
        envelope, _ = self.last()
        self.assertEqual(envelope.type, "sdk.editor.document.get")
        self.assertEqual(envelope.payload, {"documentId": "d1"})

    def test_symbols_sends_document_id_and_parses_result(self):
        received = {}
        self.docs.symbols("d1", callback=lambda result=None, **_: received.update(r=result))
        envelope, callback = self.last()
        self.assertEqual(envelope.type, "sdk.editor.document.symbols")
        callback(data={"documentId": "d1", "revision": 5, "stale": False, "symbols": []})
        self.assertIsInstance(received["r"], SymbolResult)
        self.assertEqual(received["r"].revision, 5)

    def test_symbols_forwards_unavailable_error(self):
        received = {}
        self.docs.symbols("d1", callback=lambda error=None, **_: received.update(e=error))
        _, callback = self.last()
        callback(error=RuntimeError("unavailable"))
        self.assertIsInstance(received["e"], RuntimeError)

    def test_reveal_sends_line_and_optional_column(self):
        self.docs.reveal("d1", 4, column=2)
        envelope, _ = self.last()
        self.assertEqual(envelope.type, "sdk.editor.document.reveal")
        self.assertEqual(envelope.payload, {"documentId": "d1", "line": 4, "column": 2})

    def test_get_selection_omits_document_id_when_none(self):
        self.docs.get_selection()
        envelope, _ = self.last()
        self.assertEqual(envelope.type, "sdk.editor.document.selection.get")
        self.assertEqual(envelope.payload, {})

    def test_on_changed_subscribes_to_topic(self):
        subscription = self.docs.on_changed(lambda event: None)
        envelope, _ = self.last()
        self.assertEqual(envelope.type, "sdk.events.subscribe")
        self.assertEqual(envelope.payload["topic"], "editor.document.changed")
        self.assertFalse(subscription.disposed)

    def test_on_active_changed_subscribes_to_active_topic(self):
        self.docs.on_active_changed(lambda event: None)
        envelope, _ = self.last()
        self.assertEqual(envelope.payload["topic"], "editor.activeDocument.changed")


if __name__ == "__main__":
    unittest.main()
