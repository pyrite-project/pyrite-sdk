from ....utils.ui import RFWSerializable
from ..base import Widget

class State(RFWSerializable):
    def __init__(self, widget: Widget, **kwargs: dict[str:str]):
        self.widget = widget
        self.states = kwargs
        self.to_rfw = self.widget.to_rfw