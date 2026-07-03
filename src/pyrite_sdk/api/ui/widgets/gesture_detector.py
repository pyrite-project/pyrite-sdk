from ....utils.ui import DataSerializer
from .base import Widget
from ..sentence import Var
from ....interfaces.ui import EventType
from typing import Any, Optional

class GestureDetector(Widget):
    def __init__(
        self,
        on_tap: Optional[EventType | DataSerializer | Var] = None,
        on_double_tap: Optional[EventType | DataSerializer | Var] = None,
        on_long_press: Optional[EventType | DataSerializer | Var] = None,
        on_tap_down: Optional[EventType | DataSerializer | Var] = None,
        on_tap_up: Optional[EventType | DataSerializer | Var] = None,
        on_tap_cancel: Optional[EventType | DataSerializer | Var] = None,
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
