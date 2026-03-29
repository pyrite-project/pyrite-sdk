from ...utils.ui import _serialize_value, RFWSerializable
from .event import Event

class Var(RFWSerializable):
    def __init__(self, *paths):
        self.paths = paths
    def to_rfw(self):
        return ".".join(map(str, self.paths))

def data(*paths): return Var("data", *paths)
def args(*paths): return Var("args", *paths)
def state(*paths): return Var("state", *paths)

def data_(*paths): return f"$[{data(*paths).to_rfw()}]"
def args_(*paths): return f"$[{args(*paths).to_rfw()}]"
def state_(*paths): return f"$[{state(*paths).to_rfw()}]"

class Widget(RFWSerializable):
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.args = kwargs
        self.parent = None
        self.children = []

    def setup(self):
        self.manager = self.parent.manager
        self.setup_child()

    def setup_event(self, event: Event | None):
        if not self.manager:
            raise Exception("Widget cannot find manager")
        if not event:
            return
        event.events = self.manager.events
        event.setup()

    def setup_child(self):
        if "child" in self.args and isinstance(self.args["child"], Widget):
            self.args["child"].parent = self
            self.args["child"].setup()
            self.children.append(self.args["child"])
        elif "children" in self.args and isinstance(self.args["children"], list):
            for child in self.args["children"]:
                if isinstance(child, Widget):
                    child.parent = self
                    child.setup()
                    self.children.append(child)

    def to_rfw(self):
        args_str = ", ".join(f"{key}: {_serialize_value(value)}" for (key, value) in self.args.items() if key != None and value != None)
        return f"{self.name}({args_str})"
