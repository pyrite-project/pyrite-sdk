from ....utils.ui import _serialize_value, RFWSerializable
from .var import Var
from typing import Any

class Match(RFWSerializable):
    def __init__(self, var: Var, *cases: "Case") -> None:
        self.cases: tuple["Case", ...] = cases
        self.var: Var = var

    def to_rfw(self) -> str:
        return f"switch {self.var.to_rfw()} {{ {', '.join([a_case.to_rfw() for a_case in self.cases])} }}"

class Case(RFWSerializable):
    def __init__(self, cond: Any, value: Any) -> None:
        self.cond: Any = cond
        self.value: Any = value

    def to_rfw(self) -> str:
        return f"{_serialize_value(self.cond)}: {_serialize_value(self.value)}"
