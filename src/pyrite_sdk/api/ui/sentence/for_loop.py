from ....utils.ui import RFWSerializable, _serialize_value
from ..context_manager import ContextNode
from .var import Var
from ....interfaces.ui import WidgetType
from typing import Any, Optional

class ForLoop(ContextNode):
    def __init__(self, var: str, in_list: Var | RFWSerializable | str, *widgets: WidgetType, **kwargs: Any) -> None:
        super().__init__("ForLoop", multi_child=True, **kwargs)
        self.var: str = var
        self.in_list: str = in_list.to_rfw() if isinstance(in_list, RFWSerializable) else str(in_list)
        self.page: Optional[Any] = None
        for widget in widgets:
            self.add(widget)

    def setup(self, parent: Any = None) -> None:
        if parent is not None:
            self.parent = parent
        if self.parent is None or getattr(self.parent, "page", None) is None:
            raise Exception("ForLoop cannot find page")
        self.page = self.parent.page
        for child in self.children:
            if isinstance(child, WidgetType):
                child.parent = self
                child.setup()
                continue
            setup = getattr(child, "setup", None)
            if callable(setup):
                setup(self)

    def to_rfw(self) -> str:
        result = f"...for {self.var} in {self.in_list}:\n"
        rendered_widgets = [_serialize_value(widget) for widget in self.children]
        result += ",\n".join(f"  {widget}" for widget in rendered_widgets)
        return result
