from .base import Widget, _serialize_value
from .widgets import State
from ...utils.ui import RFWSerializable

class Manager(RFWSerializable):
    def __init__(self, packages: list[str], widgets: dict[str, Widget | State]):
        self.packages = packages
        self.widgets = widgets

    def get_packages(self):
        return ';\n'.join([f"import {package}" for package in self.packages])+";\n"

    def get_widgets(self):
        result = ""
        for (name, widget) in self.widgets.items():
            state = ""
            if isinstance(widget, State):
                state = _serialize_value(widget.states)
            result += f"widget {name} {state} = {widget.to_rfw()};\n"

        return result

    def to_rfw(self):
        return f"{self.get_packages()}{self.get_widgets()}"