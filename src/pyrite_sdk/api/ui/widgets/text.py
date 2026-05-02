from .base import Widget
from ....utils.ui import DataParser
from typing import Any, Optional, Union

class Text(Widget):
    def __init__(self, text: Union[str, list, DataParser], style: Optional[Any] = None, text_direction: Optional[Any] = None, **kwargs: Any) -> None:
        super().__init__("Text",
                        text = text,
                        style = style,
                        textDirection = text_direction,
                        **kwargs)