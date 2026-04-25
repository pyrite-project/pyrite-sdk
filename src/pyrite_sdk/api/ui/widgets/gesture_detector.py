from ....utils.ui import DataSerializer

from ..base import Var, Widget
from ..event import Event
from typing import Any, Optional

class GestureDetector(Widget):
    def __init__(
        self,
        on_tap: Optional[Event | DataSerializer | Var] = None,
        on_double_tap: Optional[Event | DataSerializer | Var] = None,
        on_long_press: Optional[Event | DataSerializer | Var] = None,
        on_tap_down: Optional[Event | DataSerializer | Var] = None,
        on_tap_up: Optional[Event | DataSerializer | Var] = None,
        on_tap_cancel: Optional[Event | DataSerializer | Var] = None,
        **kwargs: Any
    ) -> None:
        super().__init__("GestureDetector",
                         onTap=on_tap,
                         onDoubleTap=on_double_tap,
                         onLongPress=on_long_press,
                         onTapDown=on_tap_down,
                         onTapUp=on_tap_up,
                         onTapCancel=on_tap_cancel,
                         **kwargs
                         )

    def setup(self) -> None:
        super().setup()
        for event in self.args.values():
            if isinstance(event, Event):
                self.setup_event(event)
