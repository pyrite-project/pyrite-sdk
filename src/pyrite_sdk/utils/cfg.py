from pathlib import Path
from typing import Any, Union
try:
    import tomllib #type: ignore
except ModuleNotFoundError:
    import tomli as tomllib #type: ignore

class CfgValue:
    def __init__(self, value: Any) -> None:
        self.value = value

    def __getattr__(self, key: str) -> Union["CfgValue", Any]:
        if isinstance(self.value, dict) and key in self.value:
            return CfgValue(self.value[key])
        raise AttributeError(f"No such attribute: {key}")

    def __repr__(self) -> str:
        return str(self.value)

class Cfg:
    def __init__(self, path: str | Path) -> None:
        self.path: Path = Path(path)
        self.data = self.reload()

    def reload(self) -> dict:
        with open(self.path, "rb") as f:
            self.data = tomllib.load(f)
        return self.data

    def __getattr__(self, key: str) -> Union["CfgValue", Any]:
        if key in self.data:
            return CfgValue(self.data[key])
        raise AttributeError(f"No such attribute: {key}")
