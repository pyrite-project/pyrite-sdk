from ..base import Widget

class TextButton(Widget):
    def __init__(self, on_pressed=None, **kwargs):
        super().__init__("TextButton",
                        onPressed = on_pressed,
                        **kwargs)
