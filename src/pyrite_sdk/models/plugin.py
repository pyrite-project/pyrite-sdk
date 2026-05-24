from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from ..interfaces.ui import PageType
from ..utils.cfg import Cfg

class Plugin(ABC):
    def __init__(self, ) -> None:
        self.pages: dict[str, PageType] = {}
        self._assets: Optional[Path] = None
        self.cfg: Optional[Cfg] = None

    @property
    def assets(self) -> Optional[Path]:
        return self._assets

    @assets.setter
    def assets(self, value: Path) -> None:
        self._assets = value
        plugin_cfg_path = self._assets / "plugin.toml"
        if plugin_cfg_path.exists():
            self.cfg = Cfg(self._assets/"plugin.toml")
        else:
            self.cfg = None
            print(f"Warning: cannot found plugin.toml in {self._assets}")

    def on_install(self): ...

    @abstractmethod
    def on_start(self): ...

    def on_pause(self): ...

    def on_resume(self): ...

    @abstractmethod
    def on_dispose(self): ...

    def on_uninstall(self): ...

    def on_refresh(self): ...
