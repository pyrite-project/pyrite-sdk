from ..base import Widget
from typing import Any

class NewWidget(Widget):
    def __init__(self, name: str, states: dict[str, Any] = {}, **kwargs: Any) -> None:
        super().__init__(name, **kwargs)
        self.states: dict[str, Any] = states

    def __repr__(self) -> str:
        kwargs = self.kwargs.copy()
        kwargs["states"] = self.states
        return f"{self.name}({','.join([f'{k}={v}' for k, v in kwargs.items()])})"