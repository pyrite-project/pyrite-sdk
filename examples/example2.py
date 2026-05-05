from pyrite_sdk.api.ui.widgets import *
from pyrite_sdk.api.ui.page import Page
from pyrite_sdk.api.ui.event import Event
from pyrite_sdk.api.ui.sentence import *
from pyrite_sdk.core.bridge import Bridge
from pyrite_sdk.models.schema import *
from pyrite_sdk.models.consts import *
from pyrite_sdk.models.plugin import Plugin


def callback(**kws):
    """Callback handler for custom widget events."""
    print("callback-custom-widget", kws)
    bridge.push(
        Message(
            cmd=MessageCommands.SEND,
            data=MessageData(
                others="CallbackMessage"
            )
        )
    )


class MyPlugin(Plugin):
    def __init__(self):
        super().__init__()

    def on_start(self):
        print("Plugin started")

    def on_refresh(self):
        print("Plugin refreshed - rebuilding pages")

        # Build pages
        page0 = self._build_page0()
        page1 = self._build_page1()
        page2 = self._build_page2()

        # Assign pages to plugin
        self.pages = {
            "home": page0,
            "page1": page1,
            "page2": page2
        }

        print("Pages initialized")

    def on_dispose(self):
        print("Plugin disposed")

    def _build_page0(self) -> Page:
        page0 = Page(packages=[Package.core.widgets, Package.core.material])
        button = NewWidget("Button", states={"down": False}).add_to(page0)

        with GestureDetector(
                on_tap_down=let(state.down, True),
                on_tap_up=let(state.down, False),
                on_tap_cancel=let(state.down, False),
                on_tap=args.on_pressed).add_to(button):
            with Container(
                margin=Match(
                    state.down,
                    Case(False, [0.0, 0.0, 8.0, 8.0]),
                    Case(True, [8.0, 8.0, 0.0, 0.0])
                ),
                decoration={
                    "type": "box",
                    "border": [{}]
                }
            ):
                VarWidget(args.child)

        root = NewWidget(Ui.root).add_to(page0)
        with Container().add_to(root) as a:
            with Column():
                Text(["Hello, ", self.data.name], text_direction=Ui.LTR)
                with TextButton(on_pressed=Event(lambda **kws: print("callback", kws), args={"id": 0})):
                    Text(["Hello, ", self.data.name], text_direction=Ui.LTR)
                with Widget("Button", on_pressed=Event(lambda **kws: callback(**kws), args={"id": 1})):
                    with TextButton():
                        Text(["Hello, ", self.data.name], text_direction=Ui.LTR)
        page0.setup_widgets()
        page0.print_tree(print_args=False)
        print(page0.to_rfw())
        return page0

    def _build_page1(self) -> Page:
        with Page(packages=[Package.core.widgets, Package.core.material]) as page1:
            with NewWidget(Ui.root):
                with Container():
                    with Center():
                        Text("test", text_direction=Ui.LTR)
        return page1

    def _build_page2(self) -> Page:
        with Page(packages=[Package.core.widgets, Package.core.material]) as page2:
            with NewWidget(Ui.root):
                with Scaffold():
                    with AppBar().alias(Ui.AppBar):
                        Text(text="Plugin Test").alias(Ui.Title)
                    with Center():
                        Text("Hello, world", text_direction=Ui.LTR)
        return page2

if __name__ == "__main__":
    plugin = MyPlugin()
    bridge = Bridge()
    bridge.start(plugin)
