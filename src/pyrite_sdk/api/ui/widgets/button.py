from .base import Widget
from ....interfaces.ui import EventType
from typing import Any, Optional

class TextButton(Widget):
    def __init__(self, on_pressed: Optional[EventType] = None, **kwargs: Any) -> None:
        super().__init__("TextButton",
                        onPressed = on_pressed,
                        **kwargs)
