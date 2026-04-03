from ..base import Widget

class State(Widget):
    def __init__(self, child: Widget, **kwargs: dict[str:str]):
        super().__init__("State")
        self.child = child
        self.states = kwargs
        self.to_rfw = self.child.to_rfw

    def setup(self):
        super().setup()
        self.child.parent = self
        self.child.manager = self.manager
        self.child.setup()
