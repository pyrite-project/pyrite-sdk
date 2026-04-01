from ..base import Widget
from ..event import Event

class GestureDetector(Widget):
    def __init__(self,
                on_tap=None,
                on_double_tap=None,
                on_long_press=None,
                on_tap_down=None,
                on_tap_up=None,
                on_tap_cancel=None,
                child=None):
        super().__init__("GestureDetector",
                         onTap=on_tap,
                         onDoubleTap=on_double_tap,
                         onLongPress=on_long_press,
                         onTapDown=on_tap_down,
                         onTapUp=on_tap_up,
                         onTapCancel=on_tap_cancel,
                         child=child)

    def setup(self):
        super().setup()
        for event in self.args.values():
            if isinstance(event, Event):
                self.setup_event(event)
