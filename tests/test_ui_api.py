import contextlib
import io
import os
import runpy
import unittest

from pyrite_sdk.api.ui.event import Event
from pyrite_sdk.api.ui.page import Page
from pyrite_sdk.api.ui.sentence import (
    Case,
    BoxDecoration,
    BorderRadius,
    Colors,
    DefaultCase,
    EdgeInsets,
    FontWeight,
    ForLoop,
    Icons,
    Match,
    TextStyle,
    Var,
    call,
    color,
    data,
    input_decoration,
    let,
    state,
    ternary,
)
from pyrite_sdk.api.ui.widgets import (
    AppBar,
    Checkbox,
    Column,
    Container,
    ElevatedButton,
    FilledButton,
    GestureDetector,
    Icon,
    IconButton,
    ListTile,
    Markdown,
    MarkdownBlock,
    MarkdownWidget,
    NewWidget,
    Padding,
    RadioGroup,
    Scaffold,
    SingleChildScrollView,
    SizedBox,
    Slider,
    Switch,
    Text,
    TextField,
)
from pyrite_sdk.models.consts import Package
from pyrite_sdk.utils.ui import DataParser


def noop(**kwargs):
    return None


class UiApiTest(unittest.TestCase):
    def make_page(self) -> tuple[Page, NewWidget]:
        page = Page(packages=[Package.core.widgets, Package.core.material])
        root = NewWidget("root").add_to(page)
        return page, root

    def test_page_to_rfw_has_no_debug_stdout_and_event_args_default(self) -> None:
        page, root = self.make_page()
        with ElevatedButton(on_pressed=Event(noop)).add_to(root):
            Text("Run")

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            rfw = page.to_rfw()

        self.assertEqual(stdout.getvalue(), "")
        self.assertIn('event "event_0" {}', rfw)
        self.assertEqual(list(page.events), ["event_0"])

    def test_gesture_detector_event_is_registered_once(self) -> None:
        page, root = self.make_page()
        with GestureDetector(on_tap=Event(noop)).add_to(root):
            Text("Tap")

        rfw = page.to_rfw()

        self.assertIn('onTap: event "event_0" {}', rfw)
        self.assertEqual(list(page.events), ["event_0"])

    def test_same_auto_event_can_be_reused_on_different_pages(self) -> None:
        event = Event(noop)

        first, first_root = self.make_page()
        with ElevatedButton(on_pressed=event).add_to(first_root):
            Text("First")
        first.to_rfw()

        second, second_root = self.make_page()
        with ElevatedButton(on_pressed=event).add_to(second_root):
            Text("Second")
        rfw = second.to_rfw()

        self.assertEqual(list(first.events), ["event_0"])
        self.assertEqual(list(second.events), ["event_0"])
        self.assertIn('event "event_0" {}', rfw)

    def test_for_loop_can_be_used_as_context_child(self) -> None:
        page, root = self.make_page()
        with Column().add_to(root):
            with ForLoop("item", data.items):
                Text(["- ", Var("item").label])

        rfw = page.to_rfw()

        self.assertIn("children: [\n  ...for item in data.items:", rfw)
        self.assertIn('    Text(text: ["- ", item.label])', rfw)

    def test_common_wrappers_serialize_to_expected_widget_names(self) -> None:
        page, root = self.make_page()
        with Scaffold(app_bar=AppBar(title=Text("Home"))).add_to(root):
            with SingleChildScrollView():
                with Padding([8, 8, 8, 8]):
                    with Column(main_axis_alignment="center"):
                        SizedBox(height=12)
                        Text("Hello", max_lines=1)

        rfw = page.to_rfw()

        self.assertIn("Scaffold(appBar: AppBar(title: Text(text: \"Home\"))", rfw)
        self.assertIn("SingleChildScrollView(child: Padding", rfw)
        self.assertIn("Column(mainAxisAlignment: \"center\"", rfw)
        self.assertIn("SizedBox(height: 12)", rfw)
        self.assertIn("Text(text: \"Hello\", maxLines: 1)", rfw)

    def test_nested_widget_args_register_events(self) -> None:
        page, root = self.make_page()
        app_bar = AppBar(
            title=Text("Home"),
            actions=[ElevatedButton(on_pressed=Event(noop))],
        )
        with Scaffold(app_bar=app_bar).add_to(root):
            Text("Body")

        rfw = page.to_rfw()

        self.assertEqual(list(page.events), ["event_0"])
        self.assertIn('actions: [ElevatedButton(onPressed: event "event_0" {})]', rfw)

    def test_data_parser_and_default_case(self) -> None:
        parsed = DataParser({"title": "Hi $[data.name]", "count": 3}).to_rfw()
        match = Match(state.kind, Case("ok", "OK"), DefaultCase("Other")).to_rfw()

        self.assertEqual(parsed, '{"title": ["Hi ", data.name], "count": 3}')
        self.assertEqual(match, 'switch state.kind { "ok": "OK", default: "Other" }')

    def test_expression_helpers_serialize_python_operations_to_rfw(self) -> None:
        condition = data.count > 2
        fallback = data.kind == "fallback"
        value = ternary(condition, "high", "low")
        set_value = let(state.enabled, ~state.enabled).to_rfw()
        decorated = BoxDecoration(
            color=ternary(state.enabled, Colors.green, Colors.red),
            border_radius=BorderRadius.circular(8),
        ).to_rfw()
        text_style = TextStyle(font_size=16, font_weight=FontWeight.bold).to_rfw()
        custom_call = call("CustomWidget", item_count=2).to_rfw()
        call_input_decoration = call("InputDecoration", label_text="Search").to_rfw()
        field_decoration = input_decoration(
            label_text="Name",
            hint_text="Type here",
            helper_text=None,
            prefix_text="$",
            suffix_text=".00",
            is_dense=True,
        ).to_rfw()

        self.assertEqual(
            condition.to_rfw(),
            "switch data.count { 0: false, 1: false, 2: false, default: true }",
        )
        self.assertEqual(
            fallback.to_rfw(),
            'switch data.kind { "fallback": true, default: false }',
        )
        self.assertEqual(
            value.to_rfw(),
            'switch data.count { 0: "low", 1: "low", 2: "low", default: "high" }',
        )
        self.assertEqual(
            set_value,
            "set state.enabled = switch state.enabled { true: false, default: true }",
        )
        self.assertEqual(
            decorated,
            '{"type": "box", "color": switch state.enabled { true: 0xff4caf50, default: 0xfff44336 }, "borderRadius": [{"x": 8.0}]}',
        )
        self.assertEqual(
            text_style,
            '{"fontSize": 16.0, "fontWeight": "w700"}',
        )
        self.assertEqual(custom_call, "CustomWidget(itemCount: 2)")
        self.assertEqual(call_input_decoration, '{"labelText": "Search"}')
        self.assertEqual(
            field_decoration,
            '{"labelText": "Name", "hintText": "Type here", "prefixText": "$", "suffixText": ".00", "isDense": true}',
        )
        count_ref = data.count
        self.assertEqual({count_ref: "count"}[count_ref], "count")
        with self.assertRaises(TypeError):
            bool(condition)
        with self.assertRaises(TypeError):
            data.count + 1
        with self.assertRaises(TypeError):
            condition & state.enabled

    def test_input_selection_and_media_wrappers_serialize_events(self) -> None:
        page, root = self.make_page()
        with Column().add_to(root):
            TextField(
                decoration={"labelText": "Name"},
                on_changed=Event(noop),
                max_lines=1,
            )
            with FilledButton(
                on_pressed=Event(noop),
                style={"backgroundColor": color(0xFF1565C0), "minimumSize": [120.0, 40.0]},
            ):
                Text("Run")
            Checkbox(
                value=state.enabled,
                on_changed=Event(noop),
                active_color=Colors.blue,
                check_color=Colors.white,
                semantic_label="Enabled",
            )
            Switch(
                value=state.enabled,
                on_changed=Event(noop),
                active_thumb_color=Colors.green,
                inactive_track_color=Colors.grey,
            )
            RadioGroup(
                group_value=data.choice,
                on_changed=Event(noop),
                items=[
                    {"value": "a", "label": "Choice A", "subtitle": "First"},
                    {"value": "b", "label": "Choice B", "enabled": False},
                ],
                active_color=Colors.blue,
                dense=True,
            )
            Slider(
                value=data.level,
                min=0.0,
                max=1.0,
                divisions=4,
                label="Level",
                on_changed=Event(noop),
            )
            ListTile(
                leading=Icon(Icons.person),
                title=Text("Profile"),
                trailing=IconButton(icon=Icon(Icons.chevron_right), on_pressed=Event(noop)),
                on_tap=Event(noop),
            )
            Padding(EdgeInsets.all(8))

        rfw = page.to_rfw()

        self.assertEqual(list(page.events), ["event_0", "event_1", "event_2", "event_3", "event_4", "event_5", "event_6", "event_7"])
        self.assertIn('TextField(decoration: {"labelText": "Name"}, maxLines: 1, onChanged: event "event_0" {})', rfw)
        self.assertIn('FilledButton(onPressed: event "event_1" {}, style: {"backgroundColor": 0xff1565c0, "minimumSize": [120.0, 40.0]}, child: Text(text: "Run"))', rfw)
        self.assertIn('Checkbox(value: state.enabled, onChanged: event "event_2" {}, activeColor: 0xff2196f3, checkColor: 0xffffffff, semanticLabel: "Enabled")', rfw)
        self.assertIn('Switch(value: state.enabled, onChanged: event "event_3" {}, activeThumbColor: 0xff4caf50, inactiveTrackColor: 0xff9e9e9e)', rfw)
        self.assertIn('RadioGroup(groupValue: data.choice, onChanged: event "event_4" {}, items: [{"value": "a", "label": "Choice A", "subtitle": "First"}, {"value": "b", "label": "Choice B", "enabled": false}], activeColor: 0xff2196f3, dense: true)', rfw)
        self.assertIn('Slider(value: data.level, onChanged: event "event_5" {}, min: 0.0, max: 1.0, divisions: 4, label: "Level")', rfw)
        self.assertIn('ListTile(leading: Icon(icon: {"icon": 0xe491, "fontFamily": "MaterialIcons"})', rfw)
        self.assertIn('trailing: GestureDetector(onTap: event "event_6" {}, child: Container', rfw)
        self.assertIn('child: Icon(icon: {"icon": 0xe15f, "fontFamily": "MaterialIcons"})', rfw)
        self.assertIn('onTap: event "event_7" {}', rfw)
        self.assertIn("Padding(padding: [8.0])", rfw)
        for unsupported in ("Radio(", "TextFormField(", "IconButton("):
            self.assertNotIn(unsupported, rfw)
        self.assertEqual(rfw.count('Icon(icon: {"icon": 0xe491, "fontFamily": "MaterialIcons"})'), 1)
        self.assertEqual(rfw.count('Text(text: "Profile")'), 1)

    def test_markdown_wrappers_serialize_events(self) -> None:
        page, root = self.make_page()
        with Column().add_to(root):
            MarkdownBlock(
                "# Title\n\n[Docs](https://example.com)",
                selectable=False,
                padding=EdgeInsets.all(12),
                on_tap_link=Event(noop),
            )
            MarkdownWidget(data.body, shrink_wrap=True, on_tap_link=Event(noop))
            Markdown(
                "Plain **markdown**",
                selectable=True,
                code_block_text_style=TextStyle(font_family="Menlo"),
                code_block_style_not_matched=TextStyle(color=color(0xFF1F2937)),
                code_block_theme="dark",
                inline_code_text_style=TextStyle(
                    font_family="Menlo",
                    background_color=color(0xFFEFF4FA),
                ),
            )

        rfw = page.to_rfw()

        self.assertEqual(list(page.events), ["event_0", "event_1"])
        self.assertIn('MarkdownBlock(data: "# Title\\n\\n[Docs](https://example.com)", selectable: false, padding: [12.0], onTapLink: event "event_0" {})', rfw)
        self.assertIn('MarkdownWidget(data: data.body, shrinkWrap: true, onTapLink: event "event_1" {})', rfw)
        self.assertIn('Markdown(data: "Plain **markdown**", selectable: true, codeBlockTextStyle: {"fontFamily": "Menlo"}, codeBlockStyleNotMatched: {"color": 0xff1f2937}, codeBlockTheme: "dark", inlineCodeTextStyle: {"fontFamily": "Menlo", "backgroundColor": 0xffeff4fa})', rfw)

    def test_ui_plugin_example_uses_only_registered_rfw_widget_names(self) -> None:
        from pyrite_sdk.core.bridge import Bridge

        original_start = Bridge.start
        original_port = os.environ.get("PYRITE_IDE_PLUGIN_PORT")
        os.environ["PYRITE_IDE_PLUGIN_PORT"] = "65530"
        Bridge.start = lambda self: None
        try:
            namespace = runpy.run_path("examples/ui_plugin/__main__.py")
        finally:
            Bridge.start = original_start
            if original_port is None:
                os.environ.pop("PYRITE_IDE_PLUGIN_PORT", None)
            else:
                os.environ["PYRITE_IDE_PLUGIN_PORT"] = original_port

        rfw = namespace["plugin"].pages["home"].to_rfw()

        for unsupported in (
            "AnimatedContainer",
            "IconButton",
            "TextFormField",
            "Radio",
        ):
            self.assertNotIn(f"{unsupported}(", rfw)
        self.assertIn("Checkbox(value: data.checkbox, onChanged: event", rfw)
        self.assertIn("Switch(value: data.switch, onChanged: event", rfw)
        self.assertIn('TextField(decoration: {"labelText": "Start typing", "hintText": "Hello PyriteProject", "isDense": true})', rfw)
        self.assertIn('ElevatedButton(onPressed: event "event_3" {}, child: Text(text: "Button1"))', rfw)
        self.assertIn('TextButton(onPressed: event "event_4" {}, child: Text(text: "Button2"))', rfw)
        self.assertIn(
            'RadioGroup(groupValue: data.radio_group_value, onChanged: event "event_5" {}, items: [{"value": "opt1", "label":',
            rfw,
        )
        self.assertNotIn("data.counter", rfw)
        self.assertNotIn("data.enabled", rfw)

    def test_markdown_plugin_example_uses_markdown_block(self) -> None:
        from pyrite_sdk.core.bridge import Bridge

        original_start = Bridge.start
        original_port = os.environ.get("PYRITE_IDE_PLUGIN_PORT")
        os.environ["PYRITE_IDE_PLUGIN_PORT"] = "65530"
        Bridge.start = lambda self: None
        try:
            namespace = runpy.run_path("examples/markdown_plugin/__main__.py")
        finally:
            Bridge.start = original_start
            if original_port is None:
                os.environ.pop("PYRITE_IDE_PLUGIN_PORT", None)
            else:
                os.environ["PYRITE_IDE_PLUGIN_PORT"] = original_port

        rfw = namespace["plugin"].pages["home"].to_rfw()

        self.assertIn("MarkdownBlock(", rfw)
        self.assertIn('onTapLink: event "event_0" {}', rfw)
        self.assertIn('Text(text: ["Last link: ", data.last_link]', rfw)
        self.assertIn('onPressed: event "event_1" {}', rfw)
        self.assertIn('Text(text: "Reset link state")', rfw)
        self.assertNotIn("set data.", rfw)

    def test_ai_plugin_home_serializes_reasoning_and_diff_content(self) -> None:
        namespace = runpy.run_path("examples/ai_plugin/__main__.py")
        content = """这里会修改文件：

[DIFF:hello.py]
```diff
--- hello.py
+++ hello.py
@@ -1,1 +1,1 @@
-print("old")
+print("new")
```

修改完成。"""

        page = namespace["build_home_page"](
            [
                {
                    "role": "assistant",
                    "reasoning_content": "需要先确认文件内容。",
                    "show_reasoning": True,
                    "content": content,
                }
            ],
            False,
            "",
            False,
        )

        rfw = page.to_rfw()

        self.assertIn('Text(text: "思考"', rfw)
        self.assertIn('Text(text: ["Diff: ", "hello.py"]', rfw)
        self.assertIn("MarkdownBlock(", rfw)


if __name__ == "__main__":
    unittest.main()
