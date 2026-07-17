from __future__ import annotations

from typing import Any

from ....utils.ui import RFWSerializable, _serialize_value


class RFWData(RFWSerializable):
    def __init__(self, value: Any, data_value: Any = None) -> None:
        self.value = value
        self.data_value = value if data_value is None else data_value

    def to_rfw(self) -> str:
        return _serialize_value(self.value)

    def to_data(self) -> Any:
        from ....utils.ui import to_data

        return to_data(self.data_value)


class RFWLiteral(RFWSerializable):
    def __init__(self, rfw_value: str, data_value: Any) -> None:
        self.rfw_value = rfw_value
        self.data_value = data_value

    def to_rfw(self) -> str:
        return self.rfw_value

    def to_data(self) -> Any:
        return self.data_value


__all__ = ["RFWData", "RFWLiteral"]
