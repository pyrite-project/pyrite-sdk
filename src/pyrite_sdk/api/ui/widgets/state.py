from ..base import Widget

class State(Widget):
    def __init__(self, widget: Widget, **kwargs: dict[str:str]):
        super().__init__("State")
        self.widget = widget
        self.states = kwargs
        self.to_rfw = self.widget.to_rfw

    def setup(self):
        super().setup()
        self.widget.parent = self
        self.widget.manager = self.manager
        self.widget.setup()
