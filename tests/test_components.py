import asyncio
import json
import unittest

from pyrite_sdk.api.components import (
    COMPONENT_SCHEMA_VERSION,
    AppBar,
    Badge,
    Button,
    Canvas,
    Checkbox,
    Column,
    Component,
    ContextMenu,
    DataTable,
    Expanded,
    Flex,
    Icon,
    IconButton,
    Menu,
    MenuCheckboxItem,
    MenuDivider,
    MenuEvent,
    MenuItem,
    Markdown,
    MarkdownLinkEvent,
    MenuShortcut,
    ListItem,
    Submenu,
    PropertyGrid,
    PropertyEntry,
    Padding,
    RangeRequest,
    Row,
    Scaffold,
    Select,
    Tab,
    Tabs,
    Text,
    TextField,
    TableRow,
    TableColumn,
    Toolbar,
    TreeView,
    TreeNode,
    VirtualList,
    collect_handlers,
)
from pyrite_sdk.api import canvas
from pyrite_sdk.api.resources import PluginResource
from pyrite_sdk.api.view import ViewProtocolError
from pyrite_sdk.api.view import Views
from pyrite_sdk.api.icons import Icons


class FakeBridge:
    def __init__(self):
        self.calls = []

    def push_wait_response(self, envelope, callback=None, client=None):
        self.calls.append((envelope, callback, client))

    def last(self):
        envelope, _, _ = self.calls[-1]
        return envelope


class ComponentShapeTest(unittest.TestCase):
    def test_schema_version_is_declared(self):
        self.assertEqual(COMPONENT_SCHEMA_VERSION, 1)

    def test_none_props_are_omitted(self):
        node = Text("hello")
        self.assertEqual(node["props"], {"value": "hello"})
        self.assertNotIn("style", node["props"])

    def test_non_interactive_components_accept_ids_for_base_controllers(self):
        components = [
            Row(id="row"),
            Column(id="column"),
            Flex(id="flex"),
            Text("text", id="text"),
            Icon(Icons.info, id="icon"),
            Badge("badge", id="badge"),
            Toolbar(id="toolbar"),
        ]
        self.assertEqual(
            [component.id for component in components],
            ["row", "column", "flex", "text", "icon", "badge", "toolbar"],
        )

    def test_props_are_camel_case_on_the_wire(self):
        node = VirtualList(id="l", item_height=18, empty_label="none")
        self.assertIn("itemHeight", node["props"])
        self.assertIn("emptyLabel", node["props"])
        self.assertNotIn("item_height", node["props"])

    def test_children_nest(self):
        node = Column(Text("a"), Text("b"), gap=4)
        self.assertEqual(node["type"], "Column")
        self.assertEqual(len(node["children"]), 2)
        self.assertEqual(node["props"], {"gap": 4})

    def test_padding_shape(self):
        node = Padding(
            Text("a"),
            id="padding",
            all_padding=12,
            left_padding=1,
            right_padding=2,
            top_padding=3,
            bottom_padding=4,
        )
        self.assertEqual(node["type"], "Padding")
        self.assertEqual(
            node["props"],
            {
                "id": "padding",
                "allPadding": 12,
                "leftPadding": 1,
                "rightPadding": 2,
                "topPadding": 3,
                "bottomPadding": 4,
            },
        )
        self.assertEqual(node["children"][0]["type"], "Text")

    def test_expanded_shape(self):
        node = Expanded(Text("a"), id="expanded", flex=2)
        self.assertEqual(node["type"], "Expanded")
        self.assertEqual(node["props"], {"id": "expanded", "flex": 2})
        self.assertEqual(node["children"][0]["type"], "Text")

    def test_app_bar_scaffold_and_canvas_match_the_native_wire_shape(self):
        refresh = IconButton(id="refresh", icon=Icons.refresh)
        page = Scaffold(
            Text("Body"),
            id="page",
            app_bar=AppBar(refresh, title="Canvas tools"),
        )
        surface = Canvas(
            id="surface",
            width=320,
            height=180,
            interactive=True,
            viewport={"scale": 2},
            ops=[canvas.rect(0, 0, 20, 10, paint=canvas.paint(color="#ff0000"))],
            on_tap=lambda payload: None,
        )

        self.assertEqual(page["children"][0]["type"], "AppBar")
        self.assertEqual(page["children"][1]["type"], "Text")
        self.assertEqual(surface["props"]["viewport"], {"scale": 2})
        self.assertEqual(surface["props"]["ops"][0]["op"], "rect")
        self.assertEqual(surface.to_json()["events"], {"tap": True})

    def test_canvas_image_requires_a_plugin_scoped_resource(self):
        resource = PluginResource("assets/preview.png")
        op = canvas.image(resource, 1, 2, width=30, height=40)
        self.assertEqual(op["src"], "plugin-resource:///assets/preview.png")
        with self.assertRaisesRegex(TypeError, "plugin.resources.asset"):
            canvas.image("assets/preview.png", 1, 2)

    def test_tabs_only_receive_tab_children(self):
        node = Tabs(Tab(Text("body"), id="t1", label="One"), selected="t1")
        self.assertEqual(node["children"][0]["type"], "Tab")

    def test_to_json_reduces_handlers_to_markers(self):
        node = Button(id="go", label="Go", on_press=lambda payload: None)
        wire = node.to_json()
        self.assertEqual(wire["events"], {"press": True})
        # And the result is serializable.
        json.dumps(wire)

    def test_to_json_is_recursive(self):
        node = Column(Row(Button(id="b", label="B", on_press=lambda p: None)))
        wire = node.to_json()
        button = wire["children"][0]["children"][0]
        self.assertEqual(button["events"], {"press": True})
        json.dumps(wire)

    def test_on_chains(self):
        node = Component("Button", {"id": "x", "label": "X"})
        self.assertIs(node.on("press", lambda p: None), node)
        self.assertIn("press", node["events"])

    def test_typed_menu_entries_serialize_and_event_is_named(self):
        received = []
        node = Menu(
            id="menu",
            label="Actions",
            items=[
                MenuItem(
                    id="refresh",
                    label="Refresh",
                    icon=Icons.refresh,
                    shortcut=MenuShortcut("r", primary=True),
                ),
                MenuDivider(),
                MenuCheckboxItem(id="auto", label="Auto", checked=True),
                Submenu(
                    label="More",
                    children=[MenuItem(id="details", label="Details")],
                ),
            ],
            on_select=received.append,
        )
        wire = node.to_json()
        self.assertEqual(wire["props"]["items"][0]["shortcut"]["key"], "r")
        self.assertEqual(wire["props"]["items"][1]["type"], "divider")
        node_event = MenuEvent({"itemId": "auto", "checked": False})
        self.assertEqual(node_event.item_id, "auto")
        self.assertFalse(node_event.checked)

    def test_typed_data_items_use_attribute_access(self):
        item = ListItem(id="item", label="Item", icon=Icons.description_outlined)
        node = TreeNode(id="node", label="Node", parent_id="root")
        row = TableRow(id="row", cells={"name": "Row"})
        self.assertEqual(
            (item.id, item.label, item.icon),
            ("item", "Item", "material:description_outlined"),
        )
        self.assertEqual(
            (node.id, node.label, node.parent_id), ("node", "Node", "root")
        )
        self.assertEqual((row.id, row.cells["name"]), ("row", "Row"))

        column = TableColumn(id="name", label="Name", flex=1)
        entry = PropertyEntry(id="value", name="value", value="42")
        self.assertEqual((column.id, column.label), ("name", "Name"))
        self.assertEqual((entry.id, entry.name, entry.value), ("value", "value", "42"))

    def test_menu_entries_expose_fixed_fields_as_attributes(self):
        shortcut = MenuShortcut("r", primary=True)
        item = MenuItem(id="refresh", label="Refresh", shortcut=shortcut)
        submenu = Submenu(id="more", label="More", children=[item])
        self.assertEqual(shortcut.key, "r")
        self.assertEqual((item.id, item.label), ("refresh", "Refresh"))
        self.assertEqual((submenu.id, submenu.label), ("more", "More"))

    def test_markdown_link_callback_receives_a_typed_event(self):
        received = []
        markdown = Markdown(
            "[Pyrite](https://example.com)",
            id="docs",
            on_link_tap=received.append,
        )
        markdown["events"]["linkTap"]({"href": "https://example.com"})
        self.assertIsInstance(received[0], MarkdownLinkEvent)
        self.assertEqual(received[0].href, "https://example.com")


class HandlerCollectionTest(unittest.TestCase):
    def test_collects_nested_handlers_keyed_by_id_and_event(self):
        page = Column(
            Toolbar(
                IconButton(id="refresh", icon=Icons.refresh, on_press=lambda p: None)
            ),
            TextField(id="search", on_change=lambda p: None, on_submit=lambda p: None),
            VirtualList(id="list", on_select=lambda p: None),
        )
        handlers = collect_handlers(page)
        self.assertEqual(
            sorted(handlers.keys()),
            [
                ("list", "select"),
                ("refresh", "press"),
                ("search", "change"),
                ("search", "submit"),
            ],
        )

    def test_components_without_an_id_contribute_nothing(self):
        node = Component("Text", {"value": "x"})
        node.on("press", lambda p: None)
        self.assertEqual(collect_handlers(node), {})

    def test_collects_from_a_list_of_roots(self):
        handlers = collect_handlers(
            [
                Button(id="a", label="A", on_press=lambda p: None),
                Button(id="b", label="B", on_press=lambda p: None),
            ]
        )
        self.assertEqual(len(handlers), 2)


class ComponentEventDispatchTest(unittest.TestCase):
    def setUp(self):
        self.bridge = FakeBridge()
        self.views = Views(self.bridge)
        self.model = self.views.create("panel", instance_id="i1")

    def test_snapshot_sends_wire_form_and_stays_serializable(self):
        self.model.snapshot(
            [Button(id="go", label="Go", on_press=lambda payload: None)]
        )
        nodes = self.bridge.last().payload["nodes"]
        self.assertEqual(nodes[0]["events"], {"press": True})
        json.dumps(nodes)

    def test_event_frame_invokes_the_handler(self):
        received = []
        self.model.snapshot([Button(id="go", label="Go", on_press=received.append)])
        self.views.handle_frame(
            "ide.view.event",
            {
                "instance": {"instanceId": "i1"},
                "componentId": "go",
                "event": "press",
                "payload": {"clicks": 1},
            },
        )
        self.assertEqual(received, [{"clicks": 1}])

    def test_dynamic_context_menu_receives_original_node_and_routes_selection(self):
        node = TreeNode(id="node:run", label="run", icon=Icons.functions)
        provided = []
        selected = []

        def provide_menu(current):
            provided.append(current)
            return ContextMenu(
                id=f"menu:{current.id}",
                items=[MenuItem(id="open", label=f"Open {current.label}")],
                on_select=selected.append,
            )

        self.model.snapshot(
            [TreeView(id="tree", nodes=[node], on_context_menu=provide_menu)]
        )
        menu = asyncio.run(
            self.model.request_context_menu("tree", {"targetId": node.id})
        )

        self.assertIs(provided[0], node)
        self.assertEqual(menu["props"]["items"][0]["label"], "Open run")
        self.assertTrue(
            self.model.dispatch_event(
                "menu:node:run",
                "select",
                {
                    "itemId": "open",
                    "targetId": node.id,
                    "targetType": "treeNode",
                },
            )
        )
        self.assertEqual(selected[0].target_id, node.id)

    def test_nested_component_handlers_dispatch(self):
        received = []
        self.model.snapshot(
            [
                Column(
                    Toolbar(
                        IconButton(
                            id="refresh", icon=Icons.refresh, on_press=received.append
                        )
                    )
                )
            ]
        )
        self.views.handle_frame(
            "ide.view.event",
            {
                "instance": {"instanceId": "i1"},
                "componentId": "refresh",
                "event": "press",
                "payload": {},
            },
        )
        self.assertEqual(received, [{}])

    def test_unknown_component_or_event_is_ignored(self):
        self.model.snapshot([Button(id="go", label="Go", on_press=lambda p: None)])
        self.assertFalse(self.model.dispatch_event("ghost", "press"))
        self.assertFalse(self.model.dispatch_event("go", "hover"))

    def test_a_new_snapshot_drops_stale_handlers(self):
        received = []
        self.model.snapshot([Button(id="old", label="Old", on_press=received.append)])
        self.model.snapshot([Button(id="new", label="New", on_press=received.append)])
        self.assertFalse(self.model.dispatch_event("old", "press"))
        self.assertTrue(self.model.dispatch_event("new", "press"))

    def test_events_route_to_the_right_instance(self):
        other = self.views.create("panel", instance_id="i2")
        first, second = [], []
        self.model.snapshot([Button(id="go", label="Go", on_press=first.append)])
        other.snapshot([Button(id="go", label="Go", on_press=second.append)])
        self.views.handle_frame(
            "ide.view.event",
            {
                "instance": {"instanceId": "i2"},
                "componentId": "go",
                "event": "press",
                "payload": {"which": "second"},
            },
        )
        self.assertEqual(first, [])
        self.assertEqual(second, [{"which": "second"}])


class ComponentControllerTest(unittest.TestCase):
    def setUp(self):
        self.bridge = FakeBridge()
        self.model = Views(self.bridge).create("panel", instance_id="i1")

    def _assert_call(self, component_type, invoke, method, arguments=None):
        component = Component(component_type, {"id": "target"})
        self.model.snapshot([component])
        callback = object()
        invoke(component.controller, callback)
        envelope, actual_callback, _ = self.bridge.calls[-1]
        self.assertEqual(envelope.type, "sdk.view.component.invoke")
        self.assertEqual(
            envelope.payload,
            {
                "viewId": "panel",
                "instanceId": "i1",
                "componentId": "target",
                "method": method,
                "arguments": arguments or {},
            },
        )
        self.assertIs(actual_callback, callback)

    def test_every_controller_method_emits_the_typed_operation(self):
        cases = [
            ("Button", lambda c, cb: c.is_mounted(cb), "is_mounted", {}),
            (
                "Button",
                lambda c, cb: c.ensure_visible(0.25, False, cb),
                "ensure_visible",
                {"alignment": 0.25, "animated": False},
            ),
            ("Button", lambda c, cb: c.get_bounds(cb), "get_bounds", {}),
            ("Button", lambda c, cb: c.request_focus(cb), "request_focus", {}),
            ("Button", lambda c, cb: c.unfocus(cb), "unfocus", {}),
            ("TextField", lambda c, cb: c.get_text(cb), "get_text", {}),
            (
                "TextField",
                lambda c, cb: c.set_text("next", cb),
                "set_text",
                {"text": "next"},
            ),
            ("TextField", lambda c, cb: c.clear(cb), "clear", {}),
            ("TextField", lambda c, cb: c.select_all(cb), "select_all", {}),
            ("TextField", lambda c, cb: c.get_selection(cb), "get_selection", {}),
            (
                "TextField",
                lambda c, cb: c.set_selection(2, 4, cb),
                "set_selection",
                {"start": 2, "end": 4},
            ),
            (
                "TextField",
                lambda c, cb: c.replace_selection("x", cb),
                "replace_selection",
                {"text": "x"},
            ),
            ("NumberField", lambda c, cb: c.get_value(cb), "get_value", {}),
            (
                "NumberField",
                lambda c, cb: c.set_value(3.5, cb),
                "set_value",
                {"value": 3.5},
            ),
            ("NumberField", lambda c, cb: c.increment(cb), "increment", {}),
            ("NumberField", lambda c, cb: c.decrement(cb), "decrement", {}),
            ("VirtualList", lambda c, cb: c.select("n1", cb), "select", {"id": "n1"}),
            ("VirtualList", lambda c, cb: c.clear_selection(cb), "clear_selection", {}),
            (
                "VirtualList",
                lambda c, cb: c.reveal_item("n1", False, cb),
                "reveal_item",
                {"id": "n1", "animated": False},
            ),
            (
                "VirtualList",
                lambda c, cb: c.jump_to_index(2, cb),
                "jump_to_index",
                {"index": 2},
            ),
            (
                "VirtualList",
                lambda c, cb: c.animate_to_index(2, cb),
                "animate_to_index",
                {"index": 2},
            ),
            (
                "VirtualList",
                lambda c, cb: c.scroll_by(20, False, cb),
                "scroll_by",
                {"delta": 20, "animated": False},
            ),
            (
                "VirtualList",
                lambda c, cb: c.get_visible_range(cb),
                "get_visible_range",
                {},
            ),
            ("TreeView", lambda c, cb: c.select("n1", cb), "select", {"id": "n1"}),
            ("TreeView", lambda c, cb: c.clear_selection(cb), "clear_selection", {}),
            (
                "TreeView",
                lambda c, cb: c.reveal("n1", False, cb),
                "reveal",
                {"id": "n1", "animated": False},
            ),
            ("TreeView", lambda c, cb: c.expand("n1", cb), "expand", {"id": "n1"}),
            ("TreeView", lambda c, cb: c.collapse("n1", cb), "collapse", {"id": "n1"}),
            ("TreeView", lambda c, cb: c.toggle("n1", cb), "toggle", {"id": "n1"}),
            ("TreeView", lambda c, cb: c.expand_all(cb), "expand_all", {}),
            ("TreeView", lambda c, cb: c.collapse_all(cb), "collapse_all", {}),
            (
                "TreeView",
                lambda c, cb: c.is_expanded("n1", cb),
                "is_expanded",
                {"id": "n1"},
            ),
            (
                "TreeView",
                lambda c, cb: c.get_visible_nodes(cb),
                "get_visible_nodes",
                {},
            ),
            (
                "PropertyGrid",
                lambda c, cb: c.activate("n1", cb),
                "activate",
                {"id": "n1"},
            ),
            (
                "DataTable",
                lambda c, cb: c.select_row("r1", cb),
                "select_row",
                {"id": "r1"},
            ),
            ("DataTable", lambda c, cb: c.clear_selection(cb), "clear_selection", {}),
            (
                "DataTable",
                lambda c, cb: c.reveal_row("r1", False, cb),
                "reveal_row",
                {"id": "r1", "animated": False},
            ),
            (
                "DataTable",
                lambda c, cb: c.reveal_cell("r1", "c1", False, cb),
                "reveal_cell",
                {"rowId": "r1", "columnId": "c1", "animated": False},
            ),
            (
                "DataTable",
                lambda c, cb: c.jump_to_row(3, cb),
                "jump_to_row",
                {"index": 3},
            ),
            (
                "DataTable",
                lambda c, cb: c.animate_to_row(3, cb),
                "animate_to_row",
                {"index": 3},
            ),
            (
                "DataTable",
                lambda c, cb: c.get_visible_range(cb),
                "get_visible_range",
                {},
            ),
            ("Tabs", lambda c, cb: c.select("tab1", cb), "select", {"id": "tab1"}),
            ("Tabs", lambda c, cb: c.next(cb), "next", {}),
            ("Tabs", lambda c, cb: c.previous(cb), "previous", {}),
            ("Tabs", lambda c, cb: c.get_selected(cb), "get_selected", {}),
            ("Section", lambda c, cb: c.expand(cb), "expand", {}),
            ("Section", lambda c, cb: c.collapse(cb), "collapse", {}),
            ("Section", lambda c, cb: c.toggle(cb), "toggle", {}),
            ("Section", lambda c, cb: c.is_expanded(cb), "is_expanded", {}),
            ("SplitView", lambda c, cb: c.get_ratios(cb), "get_ratios", {}),
            (
                "SplitView",
                lambda c, cb: c.set_ratio(0, 0.4, cb),
                "set_ratio",
                {"index": 0, "ratio": 0.4},
            ),
            (
                "SplitView",
                lambda c, cb: c.set_ratios([0.4, 0.6], cb),
                "set_ratios",
                {"ratios": [0.4, 0.6]},
            ),
            ("SplitView", lambda c, cb: c.reset(cb), "reset", {}),
            ("Video", lambda c, cb: c.play(cb), "play", {}),
            ("Video", lambda c, cb: c.pause(cb), "pause", {}),
            ("Video", lambda c, cb: c.seek_to(250, cb), "seek_to", {"positionMs": 250}),
            (
                "Video",
                lambda c, cb: c.set_volume(0.5, cb),
                "set_volume",
                {"volume": 0.5},
            ),
            ("Video", lambda c, cb: c.set_speed(1.5, cb), "set_speed", {"speed": 1.5}),
            (
                "Video",
                lambda c, cb: c.set_looping(True, cb),
                "set_looping",
                {"looping": True},
            ),
            ("Video", lambda c, cb: c.get_state(cb), "get_state", {}),
            ("Video", lambda c, cb: c.enter_fullscreen(cb), "enter_fullscreen", {}),
            ("Video", lambda c, cb: c.exit_fullscreen(cb), "exit_fullscreen", {}),
            ("Image", lambda c, cb: c.reload(cb), "reload", {}),
            ("Image", lambda c, cb: c.evict_cache(cb), "evict_cache", {}),
            ("Image", lambda c, cb: c.get_intrinsic_size(cb), "get_intrinsic_size", {}),
            (
                "Markdown",
                lambda c, cb: c.scroll_to_anchor("intro", cb),
                "scroll_to_anchor",
                {"anchor": "intro"},
            ),
            (
                "Markdown",
                lambda c, cb: c.get_anchor_offset("intro", cb),
                "get_anchor_offset",
                {"anchor": "intro"},
            ),
            ("Markdown", lambda c, cb: c.select_all(cb), "select_all", {}),
            ("Markdown", lambda c, cb: c.copy_selection(cb), "copy_selection", {}),
            ("Menu", lambda c, cb: c.open(cb), "open", {}),
            ("Menu", lambda c, cb: c.close(cb), "close", {}),
            ("Menu", lambda c, cb: c.toggle(cb), "toggle", {}),
            ("Menu", lambda c, cb: c.is_open(cb), "is_open", {}),
            (
                "MenuBar",
                lambda c, cb: c.open_menu("file", cb),
                "open_menu",
                {"id": "file"},
            ),
            ("MenuBar", lambda c, cb: c.close(cb), "close", {}),
            ("MenuBar", lambda c, cb: c.is_open(cb), "is_open", {}),
            ("Dropdown", lambda c, cb: c.open(cb), "open", {}),
            ("Dropdown", lambda c, cb: c.close(cb), "close", {}),
            ("Dropdown", lambda c, cb: c.select("one", cb), "select", {"id": "one"}),
            ("Dropdown", lambda c, cb: c.get_selected(cb), "get_selected", {}),
            ("Dropdown", lambda c, cb: c.is_open(cb), "is_open", {}),
            (
                "ContextMenu",
                lambda c, cb: c.show(10, 20, cb),
                "show",
                {"x": 10, "y": 20},
            ),
            ("ContextMenu", lambda c, cb: c.close(cb), "close", {}),
            ("ContextMenu", lambda c, cb: c.is_open(cb), "is_open", {}),
            ("Dialog", lambda c, cb: c.show(cb), "show", {}),
            ("Dialog", lambda c, cb: c.close("done", cb), "close", {"result": "done"}),
            ("Dialog", lambda c, cb: c.is_open(cb), "is_open", {}),
            (
                "Canvas",
                lambda c, cb: c.push_ops([{"op": "save"}], "preview", cb),
                "push_ops",
                {"ops": [{"op": "save"}], "layer": "preview"},
            ),
            (
                "Canvas",
                lambda c, cb: c.set_ops([{"op": "restore"}], callback=cb),
                "set_ops",
                {"ops": [{"op": "restore"}]},
            ),
            ("Canvas", lambda c, cb: c.clear(cb), "clear", {}),
            (
                "Canvas",
                lambda c, cb: c.clear_layer("preview", cb),
                "clear_layer",
                {"layer": "preview"},
            ),
            (
                "Canvas",
                lambda c, cb: c.hit_test(10, 20, cb),
                "hit_test",
                {"x": 10, "y": 20},
            ),
        ]
        for component_type, invoke, method, arguments in cases:
            with self.subTest(component_type=component_type, method=method):
                self._assert_call(component_type, invoke, method, arguments)

    def test_canvas_controller_rejects_oversized_invoke_payloads(self):
        component = Canvas(id="surface")
        self.model.snapshot([component])
        with self.assertRaises(ViewProtocolError):
            component.controller.push_ops(
                [{"op": "text", "text": "x" * (2 * 1024 * 1024)}]
            )

    def test_controller_rejects_unbound_or_unidentified_components(self):
        with self.assertRaisesRegex(RuntimeError, "not bound"):
            Component("TextField", {"id": "name"}).controller.clear()

        component = Component("TextField")
        self.model.snapshot([component])
        with self.assertRaisesRegex(ValueError, "requires an id"):
            component.controller.clear()

    def test_component_nested_in_a_model_wrapper_is_bound_and_serialized(self):
        component = TextField(id="search", value="before")
        self.model.snapshot([{"id": "root", "component": component}])
        self.assertEqual(
            self.bridge.last().payload["nodes"][0]["component"]["type"],
            "TextField",
        )
        component.controller.set_text("after")
        self.assertEqual(
            self.bridge.last().payload["componentId"],
            "search",
        )


class DataComponentTest(unittest.TestCase):
    def test_tree_view_wires_every_event(self):
        node = TreeView(
            id="tree",
            nodes=[{"id": "n1", "label": "Root"}],
            expanded_ids=["n1"],
            on_select=lambda p: None,
            on_expand=lambda p: None,
            on_request_children=lambda p: None,
        )
        self.assertEqual(node["props"]["expandedIds"], ["n1"])
        self.assertEqual(
            sorted(node["events"].keys()),
            ["expand", "requestChildren", "select"],
        )

    def test_data_table_carries_columns_and_sort_state(self):
        node = DataTable(
            id="table",
            columns=[{"id": "c1", "label": "Name", "flex": 2}],
            rows=[{"id": "r1", "cells": {"c1": "x"}}],
            sort_column="c1",
            sort_ascending=True,
            on_sort=lambda p: None,
        )
        self.assertEqual(node["props"]["sortColumn"], "c1")
        self.assertTrue(node["props"]["sortAscending"])
        self.assertIn("sort", node["events"])

    def test_data_callbacks_receive_typed_objects(self):
        tree_node = TreeNode(id="n1", label="Root")
        row = TableRow(id="r1", cells={"name": "Pyrite"})
        column = TableColumn(id="name", label="Name")
        selected = []
        sorted_columns = []
        ranges = []
        tree = TreeView(id="tree", nodes=[tree_node], on_select=selected.append)
        table = DataTable(
            id="table",
            columns=[column],
            rows=[row],
            on_sort=sorted_columns.append,
            on_request_range=ranges.append,
        )

        tree["events"]["select"]({"nodeId": "n1"})
        table["events"]["sort"]({"columnId": "name"})
        table["events"]["requestRange"]({"start": 20, "count": 50})

        self.assertIs(selected[0], tree_node)
        self.assertIs(sorted_columns[0], column)
        self.assertIsInstance(ranges[0], RangeRequest)
        self.assertEqual((ranges[0].start, ranges[0].count), (20, 50))

    def test_property_grid_and_badge_and_select_shapes(self):
        grid = PropertyGrid(id="g", entries=[{"id": "e1", "name": "x", "value": "1"}])
        self.assertEqual(grid["props"]["entries"][0]["name"], "x")

        badge = Badge("2 results", tone="info")
        self.assertEqual(badge["props"], {"label": "2 results", "tone": "info"})

        select = Select(
            id="s",
            options=[{"value": "a", "label": "A"}],
            on_change=lambda p: None,
        )
        self.assertEqual(select["props"]["options"][0]["value"], "a")

    def test_flex_and_checkbox_shapes(self):
        node = Flex(Text("x"), direction="vertical", flex=2)
        self.assertEqual(node["props"]["direction"], "vertical")
        box = Checkbox(id="c", value=True, on_change=lambda p: None)
        self.assertTrue(box["props"]["value"])


if __name__ == "__main__":
    unittest.main()
