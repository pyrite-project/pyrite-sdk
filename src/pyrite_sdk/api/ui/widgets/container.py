from ..base import Widget

class Container(Widget):
    def __init__(self, color = None, padding = None, margin = None, **kwargs):
        super().__init__("Container",
                        color = color,
                        padding = padding,
                        margin = margin,
                        **kwargs)

class Center(Widget):
    def __init__(self, padding=None, margin=None, **kwargs):
        super().__init__("Center",
                        padding=padding,
                        margin=margin,
                        **kwargs)

class Column(Widget):
    def __init__(self, padding=None, margin=None, **kwargs):
        super().__init__("Column",
                        padding=padding,
                        margin=margin,
                        mul_children=True,
                        **kwargs)

class Row(Widget):
    def __init__(self, padding=None, margin=None, **kwargs):
        super().__init__("Row",
                        padding=padding,
                        margin=margin,
                        mul_children=True,
                        **kwargs)

class Expanded(Widget):
    def __init__(self, **kwargs):
        super().__init__("Expanded",
                        **kwargs)

class FittedBox(Widget):
    def __init__(self, **kwargs):
        super().__init__("FittedBox",
                        **kwargs)