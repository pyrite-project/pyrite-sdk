from ....utils.ui import _serialize_value, RFWSerializable, DataSerializer, raw
from typing import Any

class Var(RFWSerializable):
    def __init__(self, *paths: str) -> None:
        self.paths: tuple[str, ...] = paths

    def __getattr__(self, key: str) -> "Var":
        return Var(*self.paths, key)

    def to_rfw(self) -> str:
        return ".".join(map(str, self.paths))

data = Var("data")
args = Var("args")
state = Var("state")

def data_(*paths: str) -> str: return f"$[{Var('data', *paths).to_rfw()}]"
def args_(*paths: str) -> str: return f"$[{Var('args', *paths).to_rfw()}]"
def state_(*paths: str) -> str: return f"$[{Var('state', *paths).to_rfw()}]"

def let(var: Var, value: Any) -> DataSerializer:
    return raw(f"set {var.to_rfw()} = {_serialize_value(value)}")
