from ..base import Widget
from ....utils.ui import DataSerializer

class TextButton(Widget):
    def __init__(self, on_pressed, child, **kwargs):
        super().__init__("TextButton",
                        onPressed = DataSerializer(on_pressed, serialize=False),
                        child = child,
                        **kwargs)
