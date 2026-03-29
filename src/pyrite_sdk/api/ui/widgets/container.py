from ..base import Widget

class Container(Widget):
    def __init__(self, child, color = None, padding = None, name = "Container", **kwargs):
        super().__init__(name,
                        child = child,
                        color = color,
                        padding = padding,
                        **kwargs)