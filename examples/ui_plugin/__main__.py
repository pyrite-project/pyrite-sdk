from pyrite_sdk.api.ui.event import Event
from pyrite_sdk.api.ui.page import Page
from pyrite_sdk.api.ui.sentence import *
from pyrite_sdk.api.ui.widgets import *
from pyrite_sdk.core.plugin import UiPlugin
from pyrite_sdk.models.consts import Package, Ui

def build_home_page(plugin: UiPlugin):
    home_page = Page([Package.core.widgets, Package.core.material])
    root_widget = NewWidget(Ui.root).add_to(home_page)

    with Scaffold(
        app_bar=AppBar(title=Text("UI Example"))
        ).add_to(root_widget).add(Padding(EdgeInsets.all(10)))\
        .add(Column(cross_axis_alignment=CrossAxisAlignment.start)):
        with Card().add(Padding(EdgeInsets.all(20)))\
            .add(Column()):
            with Row(main_axis_alignment=MainAxisAlignment.space_between):
                Text("开始使用 PyriteIDE")
                Checkbox(True)
            with Row(main_axis_alignment=MainAxisAlignment.space_between):
                Text("开始使用PyriteSDK")
                Switch(True)
            with Row(main_axis_alignment=MainAxisAlignment.space_between):
                Text("开始使用PyriteCLI")
                Switch(True)
        Padding(EdgeInsets.only(bottom=10))
        Divider()
        Padding(EdgeInsets.only(bottom=10))
        with Column(cross_axis_alignment=CrossAxisAlignment.stretch):
            tf = TextField(
                decoration=input_decoration(
                    label_text="Start typing",
                    hint_text="Hello PyriteProject"
                )
            )
            Padding(EdgeInsets.only(bottom=3))
            with Row():
                Text(
                    "TextField input: ",
                    style=TextStyle(color=Colors.grey)
                )
                Text(tf.args["value"])
            Padding(EdgeInsets.only(bottom=10))
            Divider()
            Padding(EdgeInsets.only(bottom=10))
            with Row():
                ElevatedButton(
                    Event(lambda **_: print("Hi")),
                ).add_to(Expanded()).add(Text("ElevatedButton"))
                Padding(EdgeInsets.only(right=5))
                TextButton(Event(lambda **_: print("Hello"))).add(Text("TextButton"))
            Padding(EdgeInsets.only(bottom=5))
            FilledButton(
                Event(lambda **kw: print(kw)),
                style=button_style(
                    background_color=Colors.blue
                )
            ).add(Text("FilledButton"))
            Padding(EdgeInsets.only(bottom=5))
            FilledButton(
                Event(lambda **kw: print(kw))
            ).add(Text("Hello PyriteProject"))
        Padding(EdgeInsets.only(bottom=10))
        Divider()
        Padding(EdgeInsets.only(bottom=10))

        with Card().add(Padding(EdgeInsets.all(20))).add(Column()):
            RadioGroup(
                items = [
                    RadioItem("Item1"),
                    RadioItem("选项2")
                ]
            )

            Slider()

    return home_page

class UiShowcasePlugin(UiPlugin):
    def __init__(self):
        super().__init__()
        self._render()

    def _render(self):
        self.pages['home'] = build_home_page(self)

    def on_refresh(self):
        self._render()

    def on_start(self):
        print("UI showcase plugin started")

    def on_dispose(self):
        print("UI showcase plugin disposed")


plugin = UiShowcasePlugin()
plugin.start()
