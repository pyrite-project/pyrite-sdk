from .base import Widget
from ....utils.ui import _serialize_value
from ....interfaces.ui import WidgetType
from typing import Any, Optional

class NewWidget(Widget):
    def __init__(self, name: str, states: Optional[dict[str, Any]] = None, **kwargs: Any) -> None:
        super().__init__(name, **kwargs)
        self.states: dict[str, Any] = states or {}

    def __repr__(self) -> str:
        kwargs = self.kwargs.copy()
        kwargs["states"] = self.states
        return f"{self.name}({','.join([f'{k}={v}' for k, v in kwargs.items()])})"
    
    def to_rfw(self):
        assert isinstance(self.child, WidgetType)
        state = _serialize_value(self.states)
        return f"widget {self.name} {state} = {self.child.to_rfw()}"
