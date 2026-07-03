from pyrite_sdk.api.ui.event import Event
from pyrite_sdk.api.ui.page import Page
from pyrite_sdk.api.ui.sentence import *
from pyrite_sdk.api.ui.widgets import *
from pyrite_sdk.core.plugin import UiPlugin
from pyrite_sdk.models.consts import Package, Ui


def make_action_tile(icon, title: str, subtitle: str, event: Event) -> ListTile:
    return ListTile(
        leading=Icon(icon, color=Colors.blue, size=28),
        title=Text(title, style=TextStyle(font_size=15, font_weight=FontWeight.bold)),
        subtitle=Text(subtitle, style=TextStyle(font_size=12, color=Colors.grey)),
        trailing=Icon(Icons.chevron_right),
        on_tap=event,
        content_padding=EdgeInsets.all(12),
    )


def build_button_demo(page: Page) -> None:
    button = NewWidget("PressableCard", states={"pressed": False}).add_to(page)
    with GestureDetector(
        on_tap_down=let(state.pressed, True),
        on_tap_up=let(state.pressed, False),
        on_tap_cancel=let(state.pressed, False),
        on_tap=args.on_pressed,
    ).add_to(button):
        with AnimatedContainer(
            duration=call("Duration", milliseconds=120),
            padding=EdgeInsets.all(14),
            margin=ternary(state.pressed, EdgeInsets.all(2), EdgeInsets.all(0)),
            decoration=BoxDecoration(
                color=ternary(state.pressed, Colors.blueGrey, Colors.blue),
                border_radius=BorderRadius.circular(10),
            ),
        ):
            VarWidget(args.child)


class AnimatedContainer(Widget):
    def __init__(self, **kwargs):
        super().__init__("AnimatedContainer", **kwargs)


home_page = Page(packages=[Package.core.widgets, Package.core.material])
build_button_demo(home_page)

home_root = NewWidget(Ui.root, states={
    "enabled": True,
    "counter": 0,
    "items": [
        {"title": "Layout wrappers", "subtitle": "Column, Row, Padding, Card"},
        {"title": "Inputs", "subtitle": "TextField, Switch, Checkbox, Slider"},
        {"title": "Expressions", "subtitle": "Colors, EdgeInsets, ternary, operators"},
    ],
}).add_to(home_page)

next_counter = Match(state.counter, Case(0, 1), Case(1, 2), Case(2, 3), DefaultCase(4))
counter_text = Match(state.counter, Case(0, "0"), Case(1, "1"), Case(2, "2"), Case(3, "3"), DefaultCase("4+"))
increment_counter = let(state.counter, next_counter)

home_fab = FloatingActionButton(
    tooltip="Increment",
    background_color=Colors.blue,
    on_pressed=increment_counter,
)
home_fab.add(Icon(Icons.add))

with Scaffold(
    app_bar=AppBar(
        title=Text("Pyrite UI Showcase"),
        actions=[
            IconButton(
                icon=Icon(Icons.info_outline),
                tooltip="About",
                on_pressed=Event(lambda **_: plugin.router.push("about")),
            )
        ],
    ),
    floating_action_button=home_fab,
).add_to(home_root):
    with SafeArea():
        with SingleChildScrollView(padding=EdgeInsets.all(16)):
            with Column(cross_axis_alignment=CrossAxisAlignment.stretch):
                with Card(elevation=2, margin=EdgeInsets.all(0)):
                    with Padding(EdgeInsets.all(16)):
                        with Column(cross_axis_alignment=CrossAxisAlignment.start):
                            Text(
                                "Declarative Python -> RFW",
                                style=TextStyle(font_size=20, font_weight=FontWeight.bold),
                            )
                            SizedBox(height=8)
                            Text(
                                ["Counter: ", counter_text],
                                style=TextStyle(font_size=16, color=Colors.blue),
                            )
                            SizedBox(height=8)
                            Text(
                                ternary(state.counter > 2, "You found the reactive bit.", "Tap + to update state.counter."),
                                style=TextStyle(font_size=13),
                            )

                SizedBox(height=14)

                with Row(cross_axis_alignment=CrossAxisAlignment.center):
                    Text("Enabled", style=TextStyle(font_size=15))
                    Spacer()
                    Switch(
                        value=state.enabled,
                        on_changed=let(state.enabled, state.enabled.not_()),
                    )

                SizedBox(height=8)

                TextField(
                    decoration=call("InputDecoration", label_text="Search UI APIs", prefix_icon=Icon(Icons.search)),
                    value=data.query,
                    text_input_action="search",
                    on_changed=Event(lambda value="", **_: plugin.bridge.let(data.query, value)),
                    on_submitted=Event(lambda value="", **_: plugin.bridge.let(data.query, value)),
                )
                SizedBox(height=8)
                Text(["Query: ", data.query], style=TextStyle(font_size=12, color=Colors.grey))

                SizedBox(height=12)

                TextField(
                    decoration=call("InputDecoration", label_text="Notes", hint_text="Write multiple lines"),
                    value=data.notes,
                    initial_value="",
                    keyboard_type="multiline",
                    text_input_action="newline",
                    min_lines=3,
                    max_lines=5,
                    on_changed=Event(lambda value="", **_: plugin.bridge.let(data.notes, value)),
                )
                SizedBox(height=8)
                Text(["Notes: ", data.notes], style=TextStyle(font_size=12, color=Colors.grey))

                SizedBox(height=14)

                with ForLoop("item", state.items):
                    make_action_tile(
                        Icons.widgets,
                        Var("item").title,
                        Var("item").subtitle,
                        increment_counter,
                    )

                SizedBox(height=14)

                with Widget("PressableCard", on_pressed=Event(lambda **_: plugin.router.push("about"))):
                    Text(
                        "Open about page",
                        style=TextStyle(font_size=16, color=Colors.white, font_weight=FontWeight.bold),
                        text_align=TextAlign.center,
                    )


about_page = Page(packages=[Package.core.widgets, Package.core.material])
about_root = NewWidget(Ui.root).add_to(about_page)

with Scaffold(
    app_bar=AppBar(
        title=Text("About UI Showcase"),
        leading=IconButton(
            icon=Icon(Icons.arrow_back),
            on_pressed=Event(lambda **_: plugin.router.pop()),
        ),
    )
).add_to(about_root):
    with SafeArea():
        with Padding(EdgeInsets.all(16)):
            with Column(cross_axis_alignment=CrossAxisAlignment.start):
                Text("What this page demonstrates", style=TextStyle(font_size=20, font_weight=FontWeight.bold))
                SizedBox(height=12)
                Text("This plugin is intentionally small, but it touches the main UI API layers:")
                SizedBox(height=8)
                Text("- typed widget wrappers")
                Text("- expression helpers")
                Text("- events and router calls")
                Text("- custom NewWidget templates")
                Spacer()
                with ElevatedButton(on_pressed=Event(lambda **_: plugin.router.pop())):
                    Text("Back")


class UiShowcasePlugin(UiPlugin):
    def __init__(self):
        super().__init__()
        self.pages = {
            "home": home_page,
            "about": about_page,
        }

    def on_start(self):
        print("UI showcase plugin started")

    def on_dispose(self):
        print("UI showcase plugin disposed")


plugin = UiShowcasePlugin()
plugin.start()
