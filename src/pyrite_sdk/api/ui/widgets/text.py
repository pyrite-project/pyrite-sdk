from ..base import Widget
from ....utils.ui import parse

class Text(Widget):
    def __init__(self, text:str | list, style = None, text_direction = None, **kwargs):
        super().__init__("Text",
                        text = parse(text) if isinstance(text, str) else text,
                        style = style,
                        textDirection = text_direction,
                        **kwargs)