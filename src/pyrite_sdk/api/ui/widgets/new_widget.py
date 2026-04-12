from ..base import Widget

class NewWidget(Widget):
    def __init__(self, name, states = {}, **kwargs):
        super().__init__(name, **kwargs)
        self.states = states

    def __repr__(self):
        kwargs = self.kwargs.copy()
        kwargs["states"] = self.states
        return f"{self.name}({','.join([f'{k}={v}' for k, v in kwargs.items()])})"