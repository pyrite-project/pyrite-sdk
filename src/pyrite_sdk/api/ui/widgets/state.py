from ..base import Widget

class State(Widget):
    def __init__(self, **kwargs: dict[str:str]):
        super().__init__("State", **kwargs)
        self.states = kwargs

    def setup(self):
        super().setup()
        self.to_rfw = self.child.to_rfw
        self.child.parent = self
        self.child.page = self.page
        self.child.setup()
