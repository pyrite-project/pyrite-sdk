from pyrite_sdk.api.ui.widgets import *
from pyrite_sdk.api.ui.manager import Manager
from pyrite_sdk.api.ui.event import Event
from pyrite_sdk.api.ui.base import data, let, state, args, Match, Case, Widget
from pyrite_sdk.core.bridge import Bridge

manager_0 = Manager(
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
                        on_pressed=Event(lambda **kws: print("callback-custom-widget", kws), args={"id": 1}),
                        child=Text(["Hi, ", data["greet"]["name"]], text_direction="ltr"),
                    ),
                ]
            )
        )
    }
)

manager_1 = Manager(
    ["core.widgets", "core.material"],
    widgets = {
        "root": Container(
            child = Center(
                child=Text(f"Bye, xxxx", text_direction="ltr")
            )
        )
    }
)

print(manager_0.to_rfw())

Bridge(
    managers = {
        "manager_0": manager_0,
        "manager_1": manager_1
    }
).start()