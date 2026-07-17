from .base import Widget
from ....utils.ui import DataParser
from typing import Any, Optional, Union

class Text(Widget):
    def __init__(
        self,
        text: Union[str, list, DataParser, Any],
        style: Optional[Any] = None,
        text_direction: Optional[Any] = None,
        text_align: Optional[Any] = None,
        soft_wrap: Optional[bool] = None,
        overflow: Optional[Any] = None,
        max_lines: Optional[int] = None,
        semantics_label: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(
            "Text",
            text = text,
            style = style,
            textDirection = text_direction,
            textAlign = text_align,
            softWrap = soft_wrap,
            overflow = overflow,
            maxLines = max_lines,
            semanticsLabel = semantics_label,
            **kwargs
        )
