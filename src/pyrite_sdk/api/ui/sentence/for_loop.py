from ....utils.ui import RFWSerializable
from .var import Var
from ....interfaces.ui import WidgetType

class ForLoop(RFWSerializable):
    def __init__(self, var: str, in_list: Var, *widgets: WidgetType) -> None:
        self.var: str = var
        self.in_list: str = in_list.to_rfw()
        self.widgets: tuple[WidgetType, ...] = widgets

    def to_rfw(self) -> str:
        result = f"...for {self.var} in {self.in_list}:\n"
        for widget in self.widgets:
            result += f"  {widget.to_rfw()},\n"
        return result