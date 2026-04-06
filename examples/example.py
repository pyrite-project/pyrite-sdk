from pyrite_sdk.api.ui.widgets import *
from pyrite_sdk.api.ui.page import Page
from pyrite_sdk.api.ui.event import Event
from pyrite_sdk.api.ui.base import data, let, state, args, Match, Case, Widget, Assets
from pyrite_sdk.core.bridge import Bridge
from pyrite_sdk.models.schema import *
from pyrite_sdk.models.consts import *

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

page_0 = Page(
    ["core.widgets", "core.material"],
    widgets = {
        "Button": State(
            child = GestureDetector(
                on_tap_down=let(state["down"], True),
                on_tap_up=let(state["down"], False),
                on_tap_cancel=let(state["down"], False),
                on_tap=args["on_pressed"],
                child=Container(
                    margin=Match(
                        state["down"],
                        Case(False, [0.0, 0.0, 8.0, 8.0]),
                        Case(True, [8.0, 8.0, 0.0, 0.0])
                    ),
                    decoration={
                        "type": "box",
                        "border": [{}]
                    },
                    child=args["child"]
                )
            ),
            down = False
        ),
        "root": Container(
            child = Column(
                children = [
                    Text(["Hello, ", data["greet"]["name"]], text_direction="ltr"),
                    TextButton(
                        on_pressed=Event(lambda **kws: print("callback", kws), args={"id": 0}),
                        child=Text(["Hello, ", data["greet"]["name"]], text_direction="ltr"),
                    ),
                    Widget(
                        "Button",
                        on_pressed=Event(callback, args={"id": 1}),
                        # child=Text(["Hi, ", data["greet"]["name"]], text_direction="ltr"),
                        child=TextButton(
                            child=Text(["Hello, ", data["greet"]["name"]], text_direction="ltr"),
                        ),
                    ),
                ]
            )
        )
    }
)

page_1 = Page(
    ["core.widgets", "core.material"],
    widgets = {
        "root": Container(
            child = Center(
                child=Text(Assets()/"a", text_direction="ltr")
            )
        )
    }
)

bridge = Bridge(
    pages = {
        "home": page_0,
        "page_1": page_1,
    }
)
bridge.start()