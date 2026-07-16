import asyncio
import contextlib
import io
import os
import runpy
import unittest
from types import SimpleNamespace

from pyrite_sdk.api.ui.event import Event
from pyrite_sdk.api.ui.page import Page
from pyrite_sdk.api.ui.sentence import (
    Alignment,
    Case,
    BoxDecoration,
    BoxFit,
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
    icon_data,
    input_decoration,
    let,
    state,
    ternary,
)
from pyrite_sdk.api.ui.widgets import (
    AppBar,
    Checkbox,
    Chip,
    Column,
    Container,
    DropdownButton,
    DropdownItem,
    ElevatedButton,
    ExpansionTile,
    FilledButton,
    GestureDetector,
    Icon,
    IconButton,
    Image,
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
    Tooltip,
    VideoPlayer,
)
from pyrite_sdk.models.consts import Package
from pyrite_sdk.models.schema import (
    CallbackBindingPayload,
    CallbackPayload,
    EventCallbackPayload,
    request,
)
from pyrite_sdk.utils.ui import DataParser


def noop(**kwargs):
    return None


class FakeWebSocket:
    def __init__(self, messages):
        self.messages = list(messages)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.messages:
            raise StopAsyncIteration
        return self.messages.pop(0)


class UiApiTest(unittest.TestCase):
    def make_page(self) -> tuple[Page, NewWidget]:
        page = Page(packages=[Package.core.widgets, Package.core.material])
        root = NewWidget("root").add_to(page)
        return page, root

    def make_bridge(self, pages=None):
        from pyrite_sdk.core.bridge import Bridge

        original_port = os.environ.get("PYRITE_IDE_PLUGIN_PORT")
        os.environ["PYRITE_IDE_PLUGIN_PORT"] = "65530"
        try:
            return Bridge(SimpleNamespace(pages=pages or {}))
        finally:
            if original_port is None:
                os.environ.pop("PYRITE_IDE_PLUGIN_PORT", None)
            else:
                os.environ["PYRITE_IDE_PLUGIN_PORT"] = original_port

    def callback_name(self, widget, event: str) -> str:
        return f"callback-{widget.widget_id}-{event}"

    def test_page_to_rfw_has_no_debug_stdout_and_event_args_default(self) -> None:
        page, root = self.make_page()
        button = ElevatedButton(on_pressed=Event(noop)).add_to(root)
        with button:
            Text("Run")

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            rfw = page.to_rfw()

        event_name = self.callback_name(button, "onPressed")
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn(f'event "{event_name}" {{}}', rfw)
        self.assertEqual(list(page.events), [event_name])

    def test_gesture_detector_event_is_registered_once(self) -> None:
        page, root = self.make_page()
        detector = GestureDetector(on_tap=Event(noop)).add_to(root)
        with detector:
            Text("Tap")

        rfw = page.to_rfw()

        event_name = self.callback_name(detector, "onTap")
        self.assertIn(f'onTap: event "{event_name}" {{}}', rfw)
        self.assertEqual(list(page.events), [event_name])

    def test_same_auto_event_can_be_reused_on_different_pages(self) -> None:
        event = Event(noop)

        first, first_root = self.make_page()
        first_button = ElevatedButton(on_pressed=event).add_to(first_root)
        with first_button:
            Text("First")
        first.to_rfw()

        second, second_root = self.make_page()
        second_button = ElevatedButton(on_pressed=event).add_to(second_root)
        with second_button:
            Text("Second")
        rfw = second.to_rfw()

        first_event = self.callback_name(first_button, "onPressed")
        second_event = self.callback_name(second_button, "onPressed")
        self.assertEqual(list(first.events), [first_event])
        self.assertEqual(list(second.events), [second_event])
        self.assertIn(f'event "{second_event}" {{}}', rfw)

    def test_widget_has_auto_incrementing_id(self) -> None:
        first = Text("First")
        second = Text("Second")

        self.assertEqual(second.widget_id, first.widget_id + 1)

    def test_refresh_sends_required_callback_names(self) -> None:
        bridge = self.make_bridge()
        envelopes = []
        bridge.push = lambda envelope, client=None: envelopes.append(envelope)
        widgets = {}

        def build_pages():
            page, root = self.make_page()
            column = Column().add_to(root)
            widgets['binding'] = Switch(value=data.enabled).add_to(column)
            button = ElevatedButton(on_pressed=Event(noop)).add_to(column)
            widgets['button'] = button
            with button:
                Text('Run')
            bridge.plugin.pages = {'home': page}

        bridge.plugin.on_refresh = build_pages

        bridge.refresh()

        callback_envelope = next(
            envelope for envelope in envelopes if envelope.type == 'sdk.callback.set'
        )
        payload = CallbackPayload(**callback_envelope.payload)
        self.assertEqual(
            payload.callbacks,
            [self.callback_name(widgets['button'], 'onPressed')],
        )
        self.assertNotIn(
            'callback_{}_onChanged'.format(widgets['binding'].widget_id),
            payload.callbacks,
        )
        bridge.clear_callback_binding()

    def test_refresh_rebinds_without_resetting_initialized_data(self) -> None:
        bridge = self.make_bridge()
        envelopes = []
        bridge.push = lambda envelope, client=None: envelopes.append(envelope)

        def build_pages():
            page, root = self.make_page()
            column = Column().add_to(root)
            Switch(value=data.enabled).add_to(column)
            TextField(value=data.name).add_to(column)
            Switch(value=True).add_to(column)
            TextField(value="initial text").add_to(column)
            bridge.plugin.pages = {"home": page}

        bridge.plugin.on_refresh = build_pages

        bridge.refresh()
        first_var_sets = [
            envelope for envelope in envelopes if envelope.type == "sdk.var.set"
        ]
        first_var_names = [envelope.payload["name"] for envelope in first_var_sets]
        envelopes.clear()

        bridge.refresh()
        second_var_sets = [
            envelope for envelope in envelopes if envelope.type == "sdk.var.set"
        ]
        second_types = [envelope.type for envelope in envelopes]

        self.assertEqual(len(first_var_sets), 4)
        self.assertIn("enabled", first_var_names)
        self.assertIn("name", first_var_names)
        self.assertEqual(second_var_sets, [])
        self.assertEqual(second_types.count("sdk.callback.clear"), 1)
        self.assertEqual(second_types.count("sdk.callback.register"), 4)
        self.assertEqual(second_types.count("sdk.page.push"), 1)
        bridge.clear_callback_binding()

    def test_register_callback_binding_sends_payload_and_binds_widget_event(self) -> None:
        bridge = self.make_bridge()
        envelopes = []
        bridge.push = lambda envelope, client=None: envelopes.append(envelope)
        widget = Switch(value=data.enabled)

        bridge.register_callback_binding(widget, "onChanged", data.enabled)

        event_name = f"callback-{widget.widget_id}-onChanged"
        self.assertEqual(envelopes[0].type, "sdk.callback.register")
        self.assertEqual(
            CallbackBindingPayload(**envelopes[0].payload),
            CallbackBindingPayload(name=event_name, var="enabled"),
        )
        self.assertIn(event_name, bridge._callback_binding_names)
        self.assertIn(f'onChanged: event "{event_name}" {{}}', widget.to_rfw())

    def test_register_callback_binding_reuses_event_callback_name(self) -> None:
        bridge = self.make_bridge()
        bridge.push = lambda envelope, client=None: None
        event = Event(noop)
        widget = Switch(value=data.enabled, on_changed=event)

        bridge.register_callback_binding(widget, "onChanged", data.enabled)
        page, root = self.make_page()
        widget.add_to(root)
        rfw = page.to_rfw()

        event_name = f"callback-{widget.widget_id}-onChanged"
        self.assertEqual(list(page.events), [event_name])
        self.assertIn(f'onChanged: event "{event_name}" {{}}', rfw)

    def test_registered_callback_binding_without_python_event_is_acknowledged(self) -> None:
        bridge = self.make_bridge(pages={"home": SimpleNamespace(events={})})
        bridge._callback_binding_names.add("callback-1-onChanged")
        payload = EventCallbackPayload(
            page="home",
            name="callback-1-onChanged",
            args={"value": True},
        )
        raw = request("ide.event.callback", payload).json()
        pushed = []
        bridge.push = lambda envelope, client=None: pushed.append(envelope)

        asyncio.run(bridge.handler(FakeWebSocket([raw])))

        self.assertEqual(pushed[-1].type, "ide.response.ok")

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
        action = ElevatedButton(on_pressed=Event(noop))
        app_bar = AppBar(
            title=Text("Home"),
            actions=[action],
        )
        with Scaffold(app_bar=app_bar).add_to(root):
            Text("Body")

        rfw = page.to_rfw()

        event_name = self.callback_name(action, "onPressed")
        self.assertEqual(list(page.events), [event_name])
        self.assertIn(f'actions: [ElevatedButton(onPressed: event "{event_name}" {{}})]', rfw)

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
            text_field = TextField(
                decoration={"labelText": "Name"},
                on_changed=Event(noop),
                max_lines=1,
            )
            filled_button = FilledButton(
                on_pressed=Event(noop),
                style={"backgroundColor": color(0xFF1565C0), "minimumSize": [120.0, 40.0]},
            )
            with filled_button:
                Text("Run")
            checkbox = Checkbox(
                value=state.enabled,
                on_changed=Event(noop),
                active_color=Colors.blue,
                check_color=Colors.white,
                semantic_label="Enabled",
            )
            switch = Switch(
                value=state.enabled,
                on_changed=Event(noop),
                active_thumb_color=Colors.green,
                inactive_track_color=Colors.grey,
            )
            radio_group = RadioGroup(
                group_value=data.choice,
                on_changed=Event(noop),
                items=[
                    {"value": "a", "label": "Choice A", "subtitle": "First"},
                    {"value": "b", "label": "Choice B", "enabled": False},
                ],
                active_color=Colors.blue,
                dense=True,
            )
            slider = Slider(
                value=data.level,
                min=0.0,
                max=1.0,
                divisions=4,
                label="Level",
                on_changed=Event(noop),
            )
            icon_button = IconButton(
                icon=Icon(Icons.chevron_right),
                on_pressed=Event(noop),
                tooltip="Next",
                icon_size=28.0,
                color=Colors.blue,
                disabled_color=Colors.grey,
                splash_radius=24.0,
                autofocus=True,
            )
            list_tile = ListTile(
                leading=Icon(Icons.person),
                title=Text("Profile"),
                trailing=icon_button,
                on_tap=Event(noop),
            )
            Padding(EdgeInsets.all(8))

        rfw = page.to_rfw()

        text_event = self.callback_name(text_field, "onChanged")
        filled_event = self.callback_name(filled_button, "onPressed")
        checkbox_event = self.callback_name(checkbox, "onChanged")
        switch_event = self.callback_name(switch, "onChanged")
        radio_event = self.callback_name(radio_group, "onChanged")
        slider_event = self.callback_name(slider, "onChanged")
        icon_event = self.callback_name(icon_button, "onPressed")
        tile_event = self.callback_name(list_tile, "onTap")
        self.assertEqual(list(page.events), [text_event, filled_event, checkbox_event, switch_event, radio_event, slider_event, icon_event, tile_event])
        self.assertIn(f'TextField(decoration: {{"labelText": "Name"}}, maxLines: 1, onChanged: event "{text_event}" {{}})', rfw)
        self.assertIn(f'FilledButton(onPressed: event "{filled_event}" {{}}, style: {{"backgroundColor": 0xff1565c0, "minimumSize": [120.0, 40.0]}}, child: Text(text: "Run"))', rfw)
        self.assertIn(f'Checkbox(value: state.enabled, onChanged: event "{checkbox_event}" {{}}, activeColor: 0xff2196f3, checkColor: 0xffffffff, semanticLabel: "Enabled")', rfw)
        self.assertIn(f'Switch(value: state.enabled, onChanged: event "{switch_event}" {{}}, activeThumbColor: 0xff4caf50, inactiveTrackColor: 0xff9e9e9e)', rfw)
        self.assertIn(f'RadioGroup(groupValue: data.choice, onChanged: event "{radio_event}" {{}}, items: [{{"value": "a", "label": "Choice A", "subtitle": "First"}}, {{"value": "b", "label": "Choice B", "enabled": false}}], activeColor: 0xff2196f3, dense: true)', rfw)
        self.assertIn(f'Slider(value: data.level, onChanged: event "{slider_event}" {{}}, min: 0.0, max: 1.0, divisions: 4, label: "Level")', rfw)
        self.assertIn('ListTile(leading: Icon(icon: 0xe491, fontFamily: "MaterialIcons")', rfw)
        self.assertIn(
            f'trailing: IconButton(icon: Icon(icon: 0xe15f, fontFamily: "MaterialIcons", matchTextDirection: true), onPressed: event "{icon_event}" {{}}, tooltip: "Next", iconSize: 28.0, color: 0xff2196f3, disabledColor: 0xff9e9e9e, splashRadius: 24.0, autofocus: true)',
            rfw,
        )
        self.assertIn(f'onTap: event "{tile_event}" {{}}', rfw)
        self.assertIn("Padding(padding: [8.0])", rfw)
        for unsupported in ("Radio(", "TextFormField("):
            self.assertNotIn(unsupported, rfw)
        self.assertEqual(rfw.count('Icon(icon: 0xe491, fontFamily: "MaterialIcons")'), 1)
        self.assertEqual(rfw.count('Text(text: "Profile")'), 1)

    def test_new_common_widgets_serialize_host_payloads(self) -> None:
        page, root = self.make_page()
        with Column().add_to(root):
            Image(
                "C:/plugin/assets/cover.png",
                source_type="file",
                width=320.0,
                height=180.0,
                scale=2.0,
                package="demo_media",
                color=Colors.blue,
                color_blend_mode="srcIn",
                fit=BoxFit.cover,
                alignment=Alignment.center,
                semantic_label="Video cover",
                exclude_from_semantics=False,
                filter_quality="high",
                gapless_playback=True,
                is_anti_alias=True,
                cache_width=640,
                cache_height=360,
            )
            Image("https://example.com/cover.png", source_type="network")
            Image("assets/images/cover.png", source_type="asset", scale=3.0)
            VideoPlayer(
                "C:/plugin/assets/demo.mp4",
                source_type="file",
                width=640.0,
                height=360.0,
                package="demo_media",
                autoplay=True,
                looping=True,
                muted=False,
                show_controls=True,
                fit=BoxFit.contain,
            )
            tooltip = Tooltip(
                "Play local video",
                constraints={"minWidth": 80.0},
                padding=EdgeInsets.all(8),
                margin=EdgeInsets.all(4),
                vertical_offset=20.0,
                prefer_below=False,
                exclude_from_semantics=True,
                text_style=TextStyle(color=Colors.white),
                text_align="center",
                wait_duration=300,
                show_duration=1500,
                exit_duration=100,
                enable_tap_to_dismiss=True,
                trigger_mode="tap",
                enable_feedback=True,
                on_triggered=Event(noop),
                ignore_pointer=False,
            )
            with tooltip:
                Text("Play")
            chip = Chip(
                label=Text("Python"),
                avatar=Text("P"),
                delete_icon=Text("x"),
                on_deleted=Event(noop),
                label_style=TextStyle(color=Colors.blue),
                label_padding=EdgeInsets.all(2),
                background_color=Colors.grey,
                padding=EdgeInsets.all(4),
                delete_icon_color=Colors.red,
                tooltip="Remove Python",
                clip_behavior="antiAlias",
                elevation=2.0,
                shadow_color=Colors.black,
                autofocus=True,
            )
            expansion = ExpansionTile(
                title=Text("Advanced"),
                leading=Text("A"),
                subtitle=Text("More options"),
                trailing=Text("+"),
                show_trailing_icon=False,
                on_expansion_changed=Event(noop),
                initially_expanded=True,
                maintain_state=True,
                tile_padding=EdgeInsets.all(8),
                expanded_alignment=Alignment.center,
                children_padding=EdgeInsets.all(12),
                background_color=Colors.white,
                collapsed_background_color=Colors.grey,
                text_color=Colors.blue,
                collapsed_text_color=Colors.black,
                icon_color=Colors.green,
                collapsed_icon_color=Colors.red,
                control_affinity="leading",
                dense=True,
            )
            with expansion:
                Text("First option")
                Text("Second option")
            dropdown = DropdownButton(
                items=[
                    DropdownItem("Auto", "auto"),
                    DropdownItem(Text("High"), "high", enabled=False),
                ],
                value=data.quality,
                on_changed=Event(noop),
                on_tap=Event(noop),
                hint=Text("Select quality"),
                disabled_hint=Text("Unavailable"),
                elevation=8,
                style=TextStyle(color=Colors.blue),
                icon=Icon(Icons.chevron_right),
                icon_size=24.0,
                icon_enabled_color=Colors.green,
                icon_disabled_color=Colors.grey,
                is_dense=True,
                is_expanded=True,
                item_height=48.0,
                menu_width=320.0,
                focus_color=Colors.white,
                autofocus=True,
                dropdown_color=Colors.white,
                menu_max_height=240.0,
                enable_feedback=False,
                alignment=Alignment.center_left,
                border_radius=BorderRadius.circular(8),
                padding=EdgeInsets.all(4),
                barrier_dismissible=False,
            )

        rfw = page.to_rfw()
        tooltip_event = self.callback_name(tooltip, "onTriggered")
        chip_event = self.callback_name(chip, "onDeleted")
        expansion_event = self.callback_name(expansion, "onExpansionChanged")
        dropdown_event = self.callback_name(dropdown, "onChanged")
        dropdown_tap_event = self.callback_name(dropdown, "onTap")
        dropdown_binding = next(
            binding
            for binding in dropdown.callback_binding_names
            if binding[0] is dropdown
        )

        self.assertEqual(dropdown_binding[1], "onChanged")
        self.assertIs(dropdown_binding[2], dropdown.args["value"])
        self.assertEqual(dropdown_binding[3], "auto")

        self.assertIn(
            'Image(source: "C:/plugin/assets/cover.png", sourceType: "file", width: 320.0, height: 180.0, scale: 2.0, package: "demo_media", color: 0xff2196f3, colorBlendMode: "srcIn", fit: "cover", alignment: {"x": 0.0, "y": 0.0}, semanticLabel: "Video cover", excludeFromSemantics: false, filterQuality: "high", gaplessPlayback: true, isAntiAlias: true, cacheWidth: 640, cacheHeight: 360)',
            rfw,
        )
        self.assertIn(
            'Image(source: "https://example.com/cover.png", sourceType: "network")',
            rfw,
        )
        self.assertIn(
            'Image(source: "assets/images/cover.png", sourceType: "asset", scale: 3.0)',
            rfw,
        )
        self.assertIn(
            'VideoPlayer(source: "C:/plugin/assets/demo.mp4", sourceType: "file", width: 640.0, height: 360.0, package: "demo_media", autoplay: true, looping: true, muted: false, showControls: true, fit: "contain")',
            rfw,
        )
        self.assertIn(
            f'Tooltip(message: "Play local video", constraints: {{"minWidth": 80.0}}, padding: [8.0], margin: [4.0], verticalOffset: 20.0, preferBelow: false, excludeFromSemantics: true, textStyle: {{"color": 0xffffffff}}, textAlign: "center", waitDuration: 300, showDuration: 1500, exitDuration: 100, enableTapToDismiss: true, triggerMode: "tap", enableFeedback: true, onTriggered: event "{tooltip_event}" {{}}, ignorePointer: false, child: Text(text: "Play"))',
            rfw,
        )
        self.assertIn(
            f'Chip(label: Text(text: "Python"), avatar: Text(text: "P"), deleteIcon: Text(text: "x"), onDeleted: event "{chip_event}" {{}}, labelStyle: {{"color": 0xff2196f3}}, labelPadding: [2.0], backgroundColor: 0xff9e9e9e, padding: [4.0], deleteIconColor: 0xfff44336, tooltip: "Remove Python", clipBehavior: "antiAlias", elevation: 2.0, shadowColor: 0xff000000, autofocus: true)',
            rfw,
        )
        self.assertIn(
            f'ExpansionTile(title: Text(text: "Advanced"), leading: Text(text: "A"), subtitle: Text(text: "More options"), trailing: Text(text: "+"), showTrailingIcon: false, onExpansionChanged: event "{expansion_event}" {{}}, initiallyExpanded: true, maintainState: true, tilePadding: [8.0], expandedAlignment: {{"x": 0.0, "y": 0.0}}, childrenPadding: [12.0], backgroundColor: 0xffffffff, collapsedBackgroundColor: 0xff9e9e9e, textColor: 0xff2196f3, collapsedTextColor: 0xff000000, iconColor: 0xff4caf50, collapsedIconColor: 0xfff44336, controlAffinity: "leading", dense: true, children: [Text(text: "First option"), Text(text: "Second option")])',
            rfw,
        )
        self.assertIn(
            f'DropdownButton(items: [{{"value": "auto", "label": "Auto", "enabled": true}}, {{"value": "high", "child": Text(text: "High"), "enabled": false}}], value: data.quality, onChanged: event "{dropdown_event}" {{}}, onTap: event "{dropdown_tap_event}" {{}}, hint: Text(text: "Select quality"), disabledHint: Text(text: "Unavailable"), elevation: 8, style: {{"color": 0xff2196f3}}, icon: Icon(icon: 0xe15f, fontFamily: "MaterialIcons", matchTextDirection: true), iconSize: 24.0, iconEnabledColor: 0xff4caf50, iconDisabledColor: 0xff9e9e9e, isDense: true, isExpanded: true, itemHeight: 48.0, menuWidth: 320.0, focusColor: 0xffffffff, autofocus: true, dropdownColor: 0xffffffff, menuMaxHeight: 240.0, enableFeedback: false, alignment: {{"x": -1.0, "y": 0.0}}, borderRadius: [{{"x": 8.0}}], padding: [4.0], barrierDismissible: false)',
            rfw,
        )
        dropdown.callback_binding_names.remove(dropdown_binding)

    def test_dropdown_binding_preserves_falsy_literal_default(self) -> None:
        for value in (0, False, ""):
            with self.subTest(value=value):
                dropdown = DropdownButton(
                    items=[DropdownItem("Selected", value)],
                    value=value,
                )
                binding = next(
                    binding
                    for binding in dropdown.callback_binding_names
                    if binding[0] is dropdown
                )
                self.assertEqual(binding[3], value)
                dropdown.callback_binding_names.remove(binding)

    def test_dropdown_item_rejects_values_the_host_cannot_decode(self) -> None:
        with self.assertRaisesRegex(TypeError, "label"):
            DropdownItem(42, "answer")
        with self.assertRaisesRegex(TypeError, "value"):
            DropdownItem("Invalid", {"nested": True})
        with self.assertRaisesRegex(ValueError, "value is required"):
            DropdownItem(Text("Missing value"))

    def test_icon_data_is_flattened_for_icon_and_icon_button(self) -> None:
        page, root = self.make_page()
        with Column().add_to(root):
            Icon(Icons.person)
            Icon(icon_data(0xE047))
            Icon({"icon": 0xE33D, "fontFamily": "MaterialIcons"})
            IconButton(icon=Icons.chevron_right)

        rfw = page.to_rfw()

        self.assertIn('Icon(icon: 0xe491, fontFamily: "MaterialIcons")', rfw)
        self.assertIn('Icon(icon: 0xe047, fontFamily: "MaterialIcons")', rfw)
        self.assertIn('Icon(icon: 58173, fontFamily: "MaterialIcons")', rfw)
        self.assertIn(
            'Icon(icon: 0xe15f, fontFamily: "MaterialIcons", matchTextDirection: true)',
            rfw,
        )
        self.assertIn(
            'IconButton(icon: Icon(icon: 0xe15f, fontFamily: "MaterialIcons", matchTextDirection: true))',
            rfw,
        )
        self.assertNotIn('Icon(icon: {"icon":', rfw)

    def test_icon_button_serializes_native_rfw_widget(self) -> None:
        page, root = self.make_page()
        with Column().add_to(root):
            icon_button = IconButton(
                icon=Icons.chevron_right,
                on_pressed=Event(noop),
                on_long_press=Event(noop),
                on_hover=Event(noop),
                selected_icon=Icons.person,
                is_selected=True,
                tooltip="Next",
                icon_size=28.0,
                visual_density={"horizontal": 1.0, "vertical": -1.0},
                padding=[4.0, 8.0],
                alignment={"x": 1.0, "y": 0.0},
                color=Colors.blue,
                disabled_color=Colors.grey,
                focus_color=color(0xFF00BCD4),
                hover_color=Colors.green,
                highlight_color=color(0xFFFFEB3B),
                splash_color=color(0xFF9C27B0),
                splash_radius=24.0,
                autofocus=True,
                enable_feedback=False,
                constraints={"minWidth": 40.0, "minHeight": 42.0},
            )

        rfw = page.to_rfw()
        press_event = self.callback_name(icon_button, "onPressed")
        long_press_event = self.callback_name(icon_button, "onLongPress")
        hover_event = self.callback_name(icon_button, "onHover")

        self.assertEqual(
            list(page.events),
            [press_event, long_press_event, hover_event],
        )
        self.assertIn(
            f'IconButton(icon: Icon(icon: 0xe15f, fontFamily: "MaterialIcons", matchTextDirection: true), selectedIcon: Icon(icon: 0xe491, fontFamily: "MaterialIcons"), onPressed: event "{press_event}" {{}}, onLongPress: event "{long_press_event}" {{}}, onHover: event "{hover_event}" {{}}',
            rfw,
        )
        self.assertIn('visualDensity: {"horizontal": 1.0, "vertical": -1.0}', rfw)
        self.assertIn('padding: [4.0, 8.0], alignment: {"x": 1.0, "y": 0.0}', rfw)
        self.assertIn(
            'color: 0xff2196f3, disabledColor: 0xff9e9e9e, focusColor: 0xff00bcd4, hoverColor: 0xff4caf50, highlightColor: 0xffffeb3b, splashColor: 0xff9c27b0',
            rfw,
        )
        self.assertIn(
            'splashRadius: 24.0, autofocus: true, enableFeedback: false, constraints: {"minWidth": 40.0, "minHeight": 42.0}, isSelected: true',
            rfw,
        )
        self.assertNotIn("GestureDetector(", rfw)

    def test_markdown_wrappers_serialize_events(self) -> None:
        page, root = self.make_page()
        with Column().add_to(root):
            markdown_block = MarkdownBlock(
                "# Title\n\n[Docs](https://example.com)",
                selectable=False,
                padding=EdgeInsets.all(12),
                on_tap_link=Event(noop),
            )
            markdown_widget = MarkdownWidget(data.body, shrink_wrap=True, on_tap_link=Event(noop))
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

        block_event = self.callback_name(markdown_block, "onTapLink")
        widget_event = self.callback_name(markdown_widget, "onTapLink")
        self.assertEqual(list(page.events), [block_event, widget_event])
        self.assertIn(f'MarkdownBlock(data: "# Title\\n\\n[Docs](https://example.com)", selectable: false, padding: [12.0], onTapLink: event "{block_event}" {{}})', rfw)
        self.assertIn(f'MarkdownWidget(data: data.body, shrinkWrap: true, onTapLink: event "{widget_event}" {{}})', rfw)
        self.assertIn('Markdown(data: "Plain **markdown**", selectable: true, codeBlockTextStyle: {"fontFamily": "Menlo"}, codeBlockStyleNotMatched: {"color": 0xff1f2937}, codeBlockTheme: "dark", inlineCodeTextStyle: {"fontFamily": "Menlo", "backgroundColor": 0xffeff4fa})', rfw)

    def test_ui_plugin_example_uses_only_registered_rfw_widget_names(self) -> None:
        namespace = runpy.run_path("examples/ui_plugin/__main__.py")
        rfw = namespace["build_home_page"]().to_rfw()

        for unsupported in (
            "AnimatedContainer",
            "IconButton",
            "TextFormField",
            "Radio",
        ):
            self.assertNotIn(f"{unsupported}(", rfw)
        for widget_name in (
            "Image",
            "VideoPlayer",
            "Tooltip",
            "Chip",
            "ExpansionTile",
            "DropdownButton",
        ):
            self.assertIn(f"{widget_name}(", rfw)

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
        self.assertRegex(rfw, r'onTapLink: event "callback-\d+-onTapLink" \{\}')
        self.assertIn('Text(text: ["Last link: ", data.last_link]', rfw)
        self.assertRegex(rfw, r'onPressed: event "callback-\d+-onPressed" \{\}')
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
