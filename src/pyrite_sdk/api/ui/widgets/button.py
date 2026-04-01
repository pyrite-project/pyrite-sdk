from ..base import Widget

class TextButton(Widget):
    def __init__(self, child, on_pressed=None, **kwargs):
        super().__init__("TextButton",
                        onPressed = on_pressed,
                        child = child,
                        **kwargs)

    def setup(self):
        super().setup()
        self.setup_event(self.args.get("onPressed"))
