from ..event import Event

from ..base import Widget
from typing import Any, Optional, Callable

class TextButton(Widget):
    def __init__(self, on_pressed: Optional[Event] = None, **kwargs: Any) -> None:
        super().__init__("TextButton",
                        onPressed = on_pressed,
                        **kwargs)
