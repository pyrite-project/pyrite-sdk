from ..base import Widget

class Scaffold(Widget):
    def __init__(self, **kwargs):
        super().__init__("Scaffold",
                        **kwargs)
        self._child_keyname = "body"

class AppBar(Widget):
    def __init__(self, **kwargs):
        super().__init__("AppBar",
                        **kwargs)
