from ..base import Widget
from typing import Any

class Scaffold(Widget):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__("Scaffold",
                        **kwargs)
        self._child_keyname = "body"

class AppBar(Widget):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__("AppBar",
                        **kwargs)
