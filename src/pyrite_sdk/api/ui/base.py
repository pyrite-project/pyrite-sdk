# from ...models.const import *
from ...utils.ui import _serialize_value, RFWSerializable
# from .widgets.base import RFWSerializable

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

    def to_rfw(self):
        args_str = ", ".join(f"{key}: {_serialize_value(value)}" for (key, value) in self.args.items() if key and value)
        return f"{self.name}({args_str})"
