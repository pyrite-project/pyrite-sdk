from .widgets import NewWidget
from .context_manager import ContextNode
from ...interfaces.ui import WidgetType, PageType
from typing import Any, Callable

class Page(ContextNode):
    def __init__(self, packages: list[str]) -> None:
        super().__init__("Page", multi_child=True)
        self.packages: list[str] = packages
        self.page: PageType = self
        self.events: dict[str, Callable[..., Any]] = {}
        self.setup_done: bool = False

    def setup_widgets(self) -> None:
        for child in self.children:
            if not isinstance(child, NewWidget):
                continue
            c = child.child
            if c is None:
                continue
            assert isinstance(c, WidgetType)
            c.page = c.parent = self
            c.setup()
        self.setup_done = True

    def get_packages(self) -> str:
        return ';'.join([f"import {package}" for package in self.packages])+";\n"

    def get_widgets(self) -> str:
        if not self.setup_done:
            self.setup_widgets()
        result: str = ""
        for child in self.children:
            assert isinstance(child, NewWidget)
            if child.child is None:
                continue
            result += child.to_rfw() + ";\n"
        return result

    def to_rfw(self) -> str:
        return f"{self.get_packages()}{self.get_widgets()}"

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        super().__exit__(exc_type, exc_val, exc_tb)
        self.setup_widgets()
        return None
