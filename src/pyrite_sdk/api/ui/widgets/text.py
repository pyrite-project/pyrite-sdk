from ..base import Widget
from ....utils.ui import DataParser

class Text(Widget):
    def __init__(self, text:str | list | DataParser, style = None, text_direction = None, **kwargs):
        super().__init__("Text",
                        text = text,
                        style = style,
                        textDirection = text_direction,
                        **kwargs)