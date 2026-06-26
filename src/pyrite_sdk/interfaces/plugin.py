from __future__ import annotations
from typing import Protocol, runtime_checkable, Optional, Callable, TYPE_CHECKING
from pathlib import Path
from ..interfaces.ui import PageType
from ..utils.cfg import Cfg

if TYPE_CHECKING:
    from ..core.bridge import Bridge

@runtime_checkable
class PluginType(Protocol):
    pages: dict[str, PageType]
    _assets: Optional[Path]
    cfg: Optional[Cfg]
    bridge: Bridge
    start: Callable

    def __init__(self, queue_size: int) -> None: ...
    @property
    def assets(self) -> Optional[Path]: ...
    @assets.setter
    def assets(self, value: Path) -> None: ...
    def on_start(self): ...
    def on_pause(self): ...
    def on_resume(self): ...
    def on_dispose(self): ...
    def on_refresh(self): ...
