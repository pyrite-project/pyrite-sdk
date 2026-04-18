from pyrite_sdk.api.ui.widgets import *
from pyrite_sdk.api.ui.page import Page
from pyrite_sdk.api.ui.event import Event
from pyrite_sdk.api.ui.base import data, let, state, args, Match, Case, Widget, Assets, VarNode
from pyrite_sdk.core.bridge import Bridge
from pyrite_sdk.models.schema import *
from pyrite_sdk.models.consts import *
from pyrite_sdk.models.plugin import Plugin

def callback(**kws):
    print("callback-custom-widget", kws)
    bridge.push(
        Message(
            cmd = MessageCommands.SEND,
            data = MessageData(
                others = "CallbackMessage"
            )
        )
    )

with Page(packages = ["core.widgets", "core.material"]) as page0:
    with NewWidget("Button", states = {"down": False}):
            with GestureDetector(
                    on_tap_down = let(state["down"], True),
                    on_tap_up = let(state["down"], False),
                    on_tap_cancel = let(state["down"], False),
                    on_tap = args["on_pressed"]):
                with Container(
                        margin=Match(
                            state["down"],
                            Case(False, [0.0, 0.0, 8.0, 8.0]),
                            Case(True, [8.0, 8.0, 0.0, 0.0])
                        ),
                        decoration={
                            "type": "box",
                            "border": [{}]
                        }):
                    VarNode(args["child"])

    with NewWidget("root"):
        with Container():
            with Column():
                Text(["Hello, ", data["greet"]["name"]], text_direction="ltr")
                with TextButton(on_pressed=Event(lambda **kws: print("callback", kws), args={"id": 0})):
                    Text(["Hello, ", data["greet"]["name"]], text_direction="ltr")
                with Widget("Button", on_pressed=Event(callback, args={"id": 1})):
                    with TextButton():
                        Text(["Hello, ", data["greet"]["name"]], text_direction="ltr"),

with Page(packages = ["core.widgets", "core.material"]) as page1:
    with NewWidget("root"):
        with Container():
            with Center():
                Text(Assets()/"a", text_direction="ltr")

page1.print_tree(print_args=True)
page0.print_tree(print_args=True)

class MyPlugin(Plugin):
    def __init__(self):
        self.pages = {
            "home": page0,
            "test": page1
        }

    def on_start(self):
        print("Plugin started")

    def on_dispose(self):
        print("Plugin disposed")

bridge = Bridge(MyPlugin())
bridge.start()
