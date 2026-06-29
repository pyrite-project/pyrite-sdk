from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from ..interfaces.ui import PageType
from ..utils.cfg import Cfg
from ..core.bridge import Bridge
from ..api.file import *
from ..api.editor import Editor
from ..api.ui.router import Router
from ..api.persistence import Persistence
from ..api.data import Theme, I18n

class Plugin(ABC):
    def __init__(self, queue_size: int = 10) -> None:
        self.pages: dict[str, PageType] = {}
        self._assets: Optional[Path] = None
        self.cfg: Optional[Cfg] = None
        self.bridge = Bridge(self, queue_size)
        self.start = self.bridge.start
        self.file = File(self.bridge)
        self.board = Board(self.bridge)
        self.editor = Editor(self.bridge)
        self.router = Router(self.bridge)
        self.persistence = Persistence(self.bridge)
        self.theme = Theme(self.bridge)
        self.i18n = I18n(self.bridge)

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

    @abstractmethod
    def on_start(self): ...
    def on_pause(self): ...
    def on_resume(self): ...
    @abstractmethod
    def on_dispose(self): ...
    def on_refresh(self): ...
