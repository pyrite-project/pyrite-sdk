import unittest
import asyncio

from pyrite_sdk.api.components import ContextMenu, MenuItem
from pyrite_sdk.api.native_views import (
    ChildrenState,
    FormField,
    LoadMoreEntry,
    LogEntry,
    MarkdownContent,
    OutlineItem,
    TableColumn,
    TableRowItem,
    TreeItem,
    VariableEntry,
    VirtualListItem,
    ViewAction,
)
from pyrite_sdk.api.view import Views
from pyrite_sdk.api.icons import Icons


class FakeBridge:
    def __init__(self):
        self.calls = []

    def push_wait_response(self, envelope, callback=None, client=None):
        self.calls.append((envelope, callback, client))

    def last(self, type):
        return next(
            envelope for envelope, _, _ in reversed(self.calls) if envelope.type == type
        )


class NativeViewTest(unittest.TestCase):
    def setUp(self):
        self.bridge = FakeBridge()
        self.views = Views(self.bridge)

    def test_outline_serializes_typed_items_and_private_action_metadata(self):
        triggered = []
        view = self.views.outline(
            "plugin.outline",
            instance_id="sidebar",
            title="大纲",
            actions=[
                ViewAction(
                    id="refresh",
                    label="刷新",
                    icon=Icons.refresh,
                    on_trigger=triggered.append,
                )
            ],
        )
        view.set_items(
            [
                OutlineItem(
                    id="symbol:run",
                    label="run",
                    icon=Icons.functions,
                    line=12,
                )
            ]
        )

        nodes = self.bridge.last("sdk.view.snapshot").payload["nodes"]
        self.assertEqual(nodes[0]["label"], "run")
        self.assertEqual(nodes[1]["role"], "appBarAction")
        self.assertEqual(nodes[1]["appBarTitle"], "大纲")

        view.model.dispatch_event(
            "plugin.outline",
            "select",
            {"nodeId": "refresh"},
        )
        self.assertEqual(triggered, [{"nodeId": "refresh"}])

    def test_outline_routes_non_action_selection_to_view_handler(self):
        received = []
        view = self.views.outline("plugin.outline", instance_id="sidebar")
        view.on_select(received.append)
        view.set_items([OutlineItem(id="symbol:run", label="run")])

        view.model.dispatch_event(
            "plugin.outline",
            "select",
            {"nodeId": "symbol:run"},
        )
        self.assertEqual(received[0].id, "symbol:run")

    def test_renderer_callbacks_receive_the_original_typed_item(self):
        node = OutlineItem(id="symbol:run", label="run", line=12, column=4)
        selected = []
        activated = []
        view = self.views.outline("plugin.outline", instance_id="sidebar")
        view.on_select(selected.append)
        view.on_activate(activated.append)
        view.set_items([node])

        view.model.dispatch_event(view.view_id, "select", {"nodeId": node.id})
        view.model.dispatch_event(view.view_id, "activate", {"nodeId": node.id})

        self.assertIs(selected[0], node)
        self.assertIs(activated[0], node)
        self.assertEqual(activated[0].line, 12)
        self.assertEqual(activated[0].column, 4)

    def test_replacing_items_uses_incremental_patch(self):
        view = self.views.outline("plugin.outline", instance_id="sidebar")
        view.set_items([OutlineItem(id="a", label="A")])
        view.set_items(
            [
                OutlineItem(id="a", label="A2"),
                OutlineItem(id="b", label="B"),
            ]
        )

        patch = self.bridge.last("sdk.view.patch")
        self.assertEqual(
            [operation["op"] for operation in patch.payload["ops"]],
            ["update", "insert"],
        )

    def test_variable_entries_hide_renderer_field_names(self):
        view = self.views.variable_inspector(
            "plugin.variables",
            instance_id="sidebar",
            title="设备变量",
        )
        entry = VariableEntry(
            id="items",
            name="items",
            type_name="list",
            value="[1]",
            has_children=True,
            children_state=ChildrenState.unloaded,
        )
        more = LoadMoreEntry(
            id="more",
            parent_id="items",
            progress="100/200",
        )
        view.set_items([entry, more])

        nodes = self.bridge.last("sdk.view.snapshot").payload["nodes"]
        self.assertEqual(nodes[0]["childrenState"], "unloaded")
        self.assertEqual(nodes[1]["role"], "loadMore")
        self.assertEqual(entry.name, "items")
        self.assertEqual(entry.type_name, "list")
        self.assertEqual(entry.value, "[1]")

    def test_renderer_view_rejects_untyped_dictionary_items(self):
        view = self.views.outline("plugin.outline", instance_id="sidebar")
        with self.assertRaises(TypeError):
            view.set_items([{"id": "raw", "label": "Raw"}])

    def test_renderer_context_menu_receives_original_typed_node(self):
        view = self.views.outline("plugin.outline", instance_id="sidebar")
        node = OutlineItem(id="symbol:run", label="run")
        received = []
        view.on_context_menu(
            lambda current: (
                received.append(current)
                or ContextMenu(
                    id=f"menu:{current.id}",
                    items=[MenuItem(id="open", label=current.label)],
                )
            )
        )
        view.set_items([node])

        menu = asyncio.run(
            view.model.request_context_menu(
                view.view_id,
                {"targetId": node.id},
            )
        )

        self.assertIs(received[0], node)
        self.assertEqual(menu["props"]["id"], "menu:symbol:run")
        nodes = self.bridge.last("sdk.view.snapshot").payload["nodes"]
        self.assertEqual(nodes[-1]["role"], "contextMenuProvider")

    def test_all_native_renderers_have_typed_facades(self):
        tree = self.views.tree("plugin.tree", searchable=True)
        tree.set_items([TreeItem(id="root", label="Root", has_children=True)])

        listing = self.views.virtual_list("plugin.list", item_count=1)
        listing.set_items([VirtualListItem(id="one", label="One")])

        table = self.views.table(
            "plugin.table",
            columns=[TableColumn(id="name", label="Name", flex=1)],
        )
        table.set_items([TableRowItem(id="row", cells={"name": "Pyrite"})])

        form = self.views.form("plugin.form")
        form.set_items([FormField(id="enabled", label="Enabled", value=True, kind="boolean")])

        markdown = self.views.markdown("plugin.markdown")
        links = []
        markdown.on_link_tap(links.append)
        markdown.set_markdown("# Pyrite")

        log = self.views.log("plugin.log", item_height=20)
        log.append(LogEntry(id="1", message="ready"))

        self.assertIsInstance(markdown.items[0], MarkdownContent)
        self.assertEqual(markdown.items[0].text, "# Pyrite")
        markdown.model.dispatch_event(
            markdown.view_id,
            "linkTap",
            {"href": "https://example.com"},
        )
        self.assertEqual(links, ["https://example.com"])
        table_nodes = self.bridge.last("sdk.view.snapshot").payload["nodes"]
        self.assertEqual(table_nodes[0]["label"], "ready")

        table_config = next(
            node for node in table.model.nodes if node.get("role") == "viewConfig"
        )
        self.assertEqual(table_config["props"]["columns"][0].id, "name")
        list_config = next(
            node for node in listing.model.nodes if node.get("role") == "viewConfig"
        )
        self.assertEqual(list_config["props"]["itemCount"], 1)


if __name__ == "__main__":
    unittest.main()
