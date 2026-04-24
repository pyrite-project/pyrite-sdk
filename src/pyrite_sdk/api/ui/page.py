from .base import _serialize_value
from .widgets import NewWidget
from .context_manager import ContextNode
from .event import Events

class Page(ContextNode):
    def __init__(self, packages: list[str]):
        super().__init__("Page", multi_child=True)
        self.packages = packages
        self.page = self
        self.events = Events()
        self.assets_directory = "ASSETS"

    def setup_widgets(self):
        for child in self.children:
            if not isinstance(child, NewWidget):
                continue
            c = child.child
            c.page = c.parent = self
            c.setup()

    def get_packages(self):
        return ';\n'.join([f"import {package}" for package in self.packages])+";\n"

    def get_widgets(self):
        result = ""
        for child in self.children:
            state = _serialize_value(child.states)
            result += f"widget {child.name} {state} = {child.child.to_rfw()};\n"

        return result

    def to_rfw(self):
        return f"{self.get_packages()}{self.get_widgets()}"

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.setup_widgets()
        return super().__exit__(exc_type, exc_val, exc_tb)