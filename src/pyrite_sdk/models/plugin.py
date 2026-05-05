from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from ..api.ui.sentence.var import Var
from ..utils.cfg import Cfg

class PluginDataRoot:
    def __init__(self, plugin: "Plugin") -> None:
        self.plugin = plugin

    def __str__(self) -> str:
        if self.plugin._data_id is not None:
            return f"data.{self.plugin._data_id}"
        return "data"

class Plugin(ABC):
    def __init__(self) -> None:
        self._assets: Optional[Path] = None
        self.cfg: Optional[Cfg] = None
        self._data_id: Optional[str] = None
        self._data_root = PluginDataRoot(self)

    @property
    def assets(self) -> Optional[Path]:
        return self._assets

    @assets.setter
    def assets(self, value: Path) -> None:
        self._assets = value
        self.cfg = Cfg(self._assets/"plugin.toml")
        self._data_id = self.cfg.general.id

    @property
    def data(self) -> Var:
        return Var(self._data_root)

    def on_install(self): ...

    @abstractmethod
    def on_start(self): ...

    def on_pause(self): ...

    def on_resume(self): ...

    @abstractmethod
    def on_dispose(self): ...

    def on_uninstall(self): ...

    def on_refresh(self): ...
