from .base import _serialize_value
from .widgets import State, NewWidget
from .context_manager import ContextNode
from .event import Events

class Page(ContextNode):
    def __init__(self, packages: list[str]):
        super().__init__("Page", mul_children=True)
        self.packages = packages
        self.page = self
        self.events = Events()
        self.assets_directory = "ASSETS"
        self.children: list[NewWidget]

    def setup_widgets(self):
        for child in self.children:
            if not isinstance(child, NewWidget):
                continue
            child.child.page = child.child.parent = self
            child.child.setup()

    def get_packages(self):
        return ';\n'.join([f"import {package}" for package in self.packages])+";\n"

    def get_widgets(self):
        result = ""
        for child in self.children:
            state = ""
            if isinstance(child.child, State):
                state = _serialize_value(child.child.states)
            result += f"widget {child.name} {state} = {child.child.to_rfw()};\n"

        return result

    def to_rfw(self):
        return f"{self.get_packages()}{self.get_widgets()}"

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.setup_widgets()
        return super().__exit__(exc_type, exc_val, exc_tb)