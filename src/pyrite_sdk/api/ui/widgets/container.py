from ..base import Widget

class Container(Widget):
    def __init__(self, child, color = None, padding = None, margin = None, **kwargs):
        super().__init__("Container",
                        child = child,
                        color = color,
                        padding = padding,
                        margin = margin,
                        **kwargs)

class Center(Widget):
    def __init__(self, child, padding=None, margin=None, **kwargs):
        super().__init__("Center",
                        child=child,
                        padding=padding,
                        margin=margin,
                        **kwargs)

class Column(Widget):
    def __init__(self, children, padding=None, margin=None, **kwargs):
        super().__init__("Column",
                        children=children,
                        padding=padding,
                        margin=margin,
                        **kwargs)

class Row(Widget):
    def __init__(self, children, padding=None, margin=None, **kwargs):
        super().__init__("Row",
                        children=children,
                        padding=padding,
                        margin=margin,
                        **kwargs)

class Expanded(Widget):
    def __init__(self, child, **kwargs):
        super().__init__("Expanded",
                        child=child,
                        **kwargs)

class FittedBox(Widget):
    def __init__(self, child, **kwargs):
        super().__init__("FittedBox",
                        child=child,
                        **kwargs)