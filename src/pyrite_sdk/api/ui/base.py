from ...utils.ui import _serialize_value, RFWSerializable
from .event import Event

class Var(RFWSerializable):
    def __init__(self, *paths):
        self.paths = paths
    
    def __getitem__(self, key):
        return Var(*self.paths, key)

    def to_rfw(self):
        return ".".join(map(str, self.paths))

data = Var("data")
args = Var("args")
state = Var("state")

def data_(*paths): return f"$[{Var('data', *paths).to_rfw()}]"
def args_(*paths): return f"$[{Var('args', *paths).to_rfw()}]"
def state_(*paths): return f"$[{Var('state', *paths).to_rfw()}]"

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

class Match(RFWSerializable):
    def __init__(self, var, *cases):
        self.cases = cases
        self.var = var
    
    def to_rfw(self):
        return f"switch {self.var} {{ {', '.join([a_case.to_rfw() for a_case in self.cases])} }}"

class Case(RFWSerializable):
    def __init__(self, cond, value):
        self.cond = cond
        self.value = value
    
    def to_rfw(self):
        return f"{_serialize_value(self.cond)}: {_serialize_value(self.value)}"

class ForLoop(RFWSerializable):
    def __init__(self, var, in_list, *widgets):
        self.var = var
        self.in_list = in_list.to_rfw()
        self.widgets = widgets
    
    def to_rfw(self):
        result = f"...for {self.var} in {self.in_list}:\n"
        for widget in self.widgets:
            result += f"  {widget.to_rfw()},\n"
        return result