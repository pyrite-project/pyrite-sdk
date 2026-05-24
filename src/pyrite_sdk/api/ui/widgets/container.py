from .base import Widget
from typing import Any, Optional

class Container(Widget):
    def __init__(self, color: Optional[Any] = None, padding: Optional[Any] = None, margin: Optional[Any] = None, **kwargs: Any) -> None:
        super().__init__("Container",
                        color = color,
                        padding = padding,
                        margin = margin,
                        **kwargs)

class Center(Widget):
    def __init__(self, padding: Optional[Any] = None, margin: Optional[Any] = None, **kwargs: Any) -> None:
        super().__init__("Center",
                        padding=padding,
                        margin=margin,
                        **kwargs)

class Column(Widget):
    def __init__(self, padding: Optional[Any] = None, margin: Optional[Any] = None, **kwargs: Any) -> None:
        super().__init__("Column",
                        padding=padding,
                        margin=margin,
                        multi_child=True,
                        **kwargs)

class Row(Widget):
    def __init__(self, padding: Optional[Any] = None, margin: Optional[Any] = None, **kwargs: Any) -> None:
        super().__init__("Row",
                        padding=padding,
                        margin=margin,
                        multi_child=True,
                        **kwargs)

class Expanded(Widget):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__("Expanded",
                        **kwargs)

class FittedBox(Widget):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__("FittedBox",
                        **kwargs)