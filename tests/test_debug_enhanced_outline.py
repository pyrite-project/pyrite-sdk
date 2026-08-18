import unittest
from pathlib import Path

from examples.debug_enhanced_plugin.outline import (
    MAX_SOURCE_BYTES,
    OPEN_EXPANSION_TAB_ID,
    OUTLINE_VIEW_ID,
    OutlineController,
    SourceTooLargeError,
    map_symbol_tree,
    scan_python_outline,
)
from pyrite_sdk.api.document import Document, DocumentSymbol, SymbolResult
from pyrite_sdk.api.tab import ViewInstanceInfo
from pyrite_sdk.api.view import Views
from pyrite_sdk.models.manifest import load_file


class FakeBridge:
    def __init__(self):
        self.calls = []

    def push_wait_response(self, envelope, callback=None, client=None):
        self.calls.append((envelope, callback, client))

    def types(self):
        return [envelope.type for envelope, _, _ in self.calls]


class FakeSubscription:
    def __init__(self):
        self.disposed = False

    def dispose(self):
        self.disposed = True


class FakeDocuments:
    def __init__(self):
        self.active_callback = None
        self.symbol_callbacks = []
        self.symbol_requests = []
        self.get_callbacks = []
        self.get_requests = []
        self.reveals = []
        self.handlers = {}

    def get_active(self, callback=None):
        self.active_callback = callback

    def get(self, document_id, callback=None):
        self.get_requests.append(document_id)
        self.get_callbacks.append(callback)

    def symbols(self, document_id, callback=None):
        self.symbol_requests.append(document_id)
        self.symbol_callbacks.append(callback)

    def reveal(self, document_id, line, column=None, callback=None):
        self.reveals.append((document_id, line, column))

    def _subscribe(self, topic, handler, **kwargs):
        self.handlers[topic] = (handler, kwargs)
        return FakeSubscription()

    def on_active_changed(self, handler, **kwargs):
        return self._subscribe("active", handler, **kwargs)

    def on_changed(self, handler, **kwargs):
        return self._subscribe("changed", handler, **kwargs)

    def on_saved(self, handler, **kwargs):
        return self._subscribe("saved", handler, **kwargs)


class FakeTabs:
    def __init__(self):
        self.calls = []

    def create_view(self, view_id, **kwargs):
        self.calls.append((view_id, kwargs))


def symbol(name, kind, line, column=0, children=None, end_line=None):
    return DocumentSymbol.from_json(
        {
            "name": name,
            "kind": kind,
            "range": {
                "start": {"line": line, "character": column},
                "end": {
                    "line": end_line if end_line is not None else line,
                    "character": column + 1,
                },
            },
            "selectionRange": {
                "start": {"line": line, "character": column},
                "end": {"line": line, "character": column + 1},
            },
            "children": children or [],
        }
    )


def flat_symbol(name, kind, start, end, *, container=None):
    raw = {
        "name": name,
        "kind": kind,
        "location": {
            "uri": "file:///main.py",
            "range": {
                "start": {"line": start, "character": 0},
                "end": {"line": end, "character": 0},
            },
        },
    }
    if container is not None:
        raw["containerName"] = container
    return DocumentSymbol.from_json(raw)


class OutlineMappingTest(unittest.TestCase):
    def test_manifest_is_a_real_native_outline_plugin(self):
        manifest = load_file(Path("examples/debug_enhanced_plugin/plugin.toml"))
        self.assertEqual(manifest.id, "debug-enhanced")
        self.assertEqual(manifest.manifest_version, 2)
        self.assertEqual(manifest.contributes.views[0].renderer, "native.outline")
        self.assertEqual(
            manifest.contributes.views[1].renderer, "native.variableInspector"
        )
        self.assertIn("editor.write", manifest.permissions)
        self.assertIn("tab.create", manifest.permissions)
        self.assertIn("runtime.inspect", manifest.permissions)

    def test_mapping_is_hierarchical_and_stable(self):
        symbols = [
            symbol(
                "Widget",
                5,
                2,
                children=[
                    {
                        "name": "build",
                        "kind": 6,
                        "selectionRange": {
                            "start": {"line": 8, "character": 4},
                            "end": {"line": 8, "character": 9},
                        },
                    }
                ],
            )
        ]
        first, locations = map_symbol_tree(symbols)
        second, _ = map_symbol_tree(symbols)
        self.assertEqual(
            [node["id"] for node in first], [node["id"] for node in second]
        )
        self.assertEqual(first[1]["parentId"], first[0]["id"])
        self.assertEqual(locations[first[1]["id"]], (8, 4))

    def test_all_lsp_symbol_kinds_have_semantic_icons_and_colors(self):
        nodes, _ = map_symbol_tree(
            [symbol(f"kind_{kind}", kind, kind) for kind in range(1, 27)]
        )
        self.assertEqual(len({node["icon"] for node in nodes}), 26)
        self.assertTrue(
            all(
                node["iconColor"] in {"primary", "secondary", "tertiary", "muted"}
                for node in nodes
            )
        )

    def test_flat_lsp_symbols_use_range_and_container_hierarchy(self):
        symbols = [
            flat_symbol("Widget", 5, 1, 20),
            flat_symbol("build", 6, 3, 8, container="Widget"),
            flat_symbol("local", 12, 4, 5, container="build"),
            flat_symbol("outside", 12, 30, 31),
        ]
        nodes, _ = map_symbol_tree(symbols)
        by_label = {node["label"]: node for node in nodes}
        self.assertEqual(by_label["build"]["parentId"], by_label["Widget"]["id"])
        self.assertEqual(by_label["local"]["parentId"], by_label["build"]["id"])
        self.assertIsNone(by_label["outside"]["parentId"])

    def test_source_scanner_matches_thonny_style_in_incomplete_code(self):
        symbols = scan_python_outline(
            "class Widget:\n"
            "    def build(self):\n"
            "        async def load(\n"
            "            pass\n"
            "def outside():\n"
            "    return 1\n"
        )
        self.assertEqual([item.name for item in symbols], ["Widget", "outside"])
        self.assertEqual([item.name for item in symbols[0].children], ["build"])
        self.assertEqual(
            [item.name for item in symbols[0].children[0].children], ["load"]
        )

    def test_source_scanner_rejects_oversized_text(self):
        with self.assertRaises(SourceTooLargeError):
            scan_python_outline("x" * (MAX_SOURCE_BYTES + 1))
        with self.assertRaises(SourceTooLargeError):
            scan_python_outline("\n" * 20_000)


class OutlineControllerTest(unittest.TestCase):
    def setUp(self):
        self.bridge = FakeBridge()
        self.views = Views(self.bridge)
        self.view = self.views.outline(
            OUTLINE_VIEW_ID,
            instance_id="container:debug-enhanced",
            title="大纲",
        )
        self.model = self.view.model
        self.documents = FakeDocuments()
        self.tabs = FakeTabs()
        self.controller = OutlineController(
            self.documents,
            self.view,
            tabs=self.tabs,
            views=self.views,
        )
        self.controller.start()

    def activate(self, document_id="doc-a"):
        self.documents.active_callback(
            document=Document(
                document_id=document_id,
                file_path=f"/{document_id}.py",
                revision=1,
                is_active=True,
            )
        )

    def complete(self, document_id, symbols, *, stale=False, index=-1):
        self.documents.symbol_callbacks[index](
            result=SymbolResult(
                document_id=document_id,
                revision=1,
                stale=stale,
                symbols=symbols,
            )
        )

    def labels(self):
        return [node["label"] for node in self.controller._rendered_nodes]

    def test_subscribes_with_debounce_and_uses_incremental_patch(self):
        self.assertEqual(
            self.documents.handlers["changed"][1],
            {"delivery": "debounce", "debounce_ms": 100},
        )
        self.activate()
        self.complete("doc-a", [symbol("main", 12, 3)])
        self.assertEqual(self.bridge.types().count("sdk.view.snapshot"), 1)
        self.assertEqual(self.bridge.types().count("sdk.view.patch"), 1)
        self.assertIn("main", self.labels())

    def test_fast_document_switch_drops_late_symbols(self):
        self.activate("doc-a")
        self.documents.handlers["active"][0](
            {"documentId": "doc-b", "filePath": "/doc-b.py", "revision": 1}
        )
        self.complete("doc-b", [symbol("new_file", 12, 10)], index=1)
        self.complete("doc-a", [symbol("old_file", 12, 1)], index=0)
        self.assertIn("new_file", self.labels())
        self.assertNotIn("old_file", self.labels())

    def test_missing_or_non_text_tab_shows_placeholder(self):
        self.documents.active_callback(document=None)
        placeholder = self.controller._content_nodes[0]
        self.assertEqual(placeholder["state"], "no-document")
        self.assertEqual(placeholder["role"], "placeholder")

    def test_tab_actions_are_rendered_in_app_bar(self):
        actions = self.controller._actions()
        self.assertEqual([action.id for action in actions], [OPEN_EXPANSION_TAB_ID])
        self.assertEqual(actions[0].label, "在拓展区打开大纲")

    def test_click_reveals_the_symbol_position(self):
        self.activate()
        self.complete("doc-a", [symbol("target", 12, 42, 7)])
        node_id = next(
            node["id"]
            for node in self.controller._rendered_nodes
            if node["label"] == "target"
        )
        self.model.dispatch_event(OUTLINE_VIEW_ID, "select", {"nodeId": node_id})
        self.assertEqual(self.documents.reveals, [("doc-a", 42, 7)])

    def test_hidden_view_pauses_refresh_until_visible(self):
        self.activate()
        self.complete("doc-a", [symbol("first", 12, 1)])
        before = len(self.documents.symbol_requests)
        self.model.visibility_sync(False)
        self.documents.handlers["changed"][0]({"documentId": "doc-a", "revision": 2})
        self.assertEqual(len(self.documents.symbol_requests), before)
        self.model.visibility_sync(True)
        self.assertEqual(len(self.documents.symbol_requests), before + 1)

    def test_unavailable_lsp_falls_back_to_current_source(self):
        self.activate()
        self.documents.symbol_callbacks[-1](error=RuntimeError("unavailable"))
        self.assertEqual(self.documents.get_requests, ["doc-a"])
        self.documents.get_callbacks[-1](
            document=Document(
                document_id="doc-a",
                file_path="/doc-a.py",
                text="class Device:\n    def connect(self):\n        pass\n",
            )
        )
        by_label = {node["label"]: node for node in self.controller._rendered_nodes}
        self.assertEqual(by_label["connect"]["parentId"], by_label["Device"]["id"])

    def test_empty_lsp_result_also_uses_source_fallback(self):
        self.activate()
        self.complete("doc-a", [])
        self.documents.get_callbacks[-1](
            document=Document(
                document_id="doc-a", file_path="/doc-a.py", text="def fallback():\n"
            )
        )
        self.assertIn("fallback", self.labels())

    def test_late_source_fallback_is_dropped_after_document_switch(self):
        self.activate("doc-a")
        self.documents.symbol_callbacks[-1](error=RuntimeError("unavailable"))
        late_callback = self.documents.get_callbacks[-1]
        self.documents.handlers["active"][0](
            {"documentId": "doc-b", "filePath": "/doc-b.py", "revision": 1}
        )
        self.complete("doc-b", [symbol("current", 12, 1)], index=1)
        late_callback(
            document=Document(
                document_id="doc-a", file_path="/doc-a.py", text="def stale():\n"
            )
        )
        self.assertIn("current", self.labels())
        self.assertNotIn("stale", self.labels())

    def test_large_fallback_source_reports_limit(self):
        self.activate()
        self.documents.symbol_callbacks[-1](error=RuntimeError("unavailable"))
        self.documents.get_callbacks[-1](
            document=Document(
                document_id="doc-a",
                file_path="/doc-a.py",
                text="x" * (MAX_SOURCE_BYTES + 1),
            )
        )
        self.assertEqual(self.controller._content_nodes[0]["state"], "too-large")

    def test_action_can_create_expansion_tab(self):
        self.activate()
        self.complete("doc-a", [symbol("main", 12, 3)])
        self.model.dispatch_event(
            OUTLINE_VIEW_ID, "select", {"nodeId": OPEN_EXPANSION_TAB_ID}
        )
        view_id, kwargs = self.tabs.calls[-1]
        self.assertEqual(view_id, OUTLINE_VIEW_ID)
        self.assertTrue(kwargs["expansion"])
        kwargs["callback"](
            instance=ViewInstanceInfo(
                "debug-enhanced", "session", OUTLINE_VIEW_ID, "tab:1"
            )
        )
        tab_model = self.views.get("tab:1")
        self.assertIsNotNone(tab_model)
        self.assertEqual(
            [node["label"] for node in tab_model.nodes],
            self.labels(),
        )


if __name__ == "__main__":
    unittest.main()
