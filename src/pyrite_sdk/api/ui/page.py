from .base import Widget, _serialize_value
from .widgets import NewWidget
from .context_manager import ContextNode
from .event import Events
from typing import Any

class Page(ContextNode):
    def __init__(self, packages: list[str]) -> None:
        super().__init__("Page", multi_child=True)
        self.packages: list[str] = packages
        self.page: Page = self
        self.events: Events = Events()
        self.assets_directory: str = "ASSETS"

    def setup_widgets(self) -> None:
        for child in self.children:
            if not isinstance(child, NewWidget):
                continue
            c = child.child
            if c is None:
                continue
            assert isinstance(c, Widget)
            c.page = c.parent = self
            c.setup()

    def get_packages(self) -> str:
        return ';'.join([f"import {package}" for package in self.packages])+";\n"

    def get_widgets(self) -> str:
        result: str = ""
        for child in self.children:
            assert isinstance(child, NewWidget)
            assert child.child is not None
            state = _serialize_value(child.states)
            result += f"widget {child.name} {state} = {child.child.to_rfw()};\n"
        return result

    def to_rfw(self) -> str:
        return f"{self.get_packages()}{self.get_widgets()}"

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.setup_widgets()
        return super().__exit__(exc_type, exc_val, exc_tb)