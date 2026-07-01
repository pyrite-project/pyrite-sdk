from __future__ import annotations
from typing import Protocol, runtime_checkable, Optional, Callable, TYPE_CHECKING
from pathlib import Path as FilePath
from ..interfaces.ui import PageType
from ..utils.cfg import Cfg

if TYPE_CHECKING:
    from ..core.bridge import Bridge

@runtime_checkable
class PluginType(Protocol):
    _assets: Optional[FilePath]
    cfg: Optional[Cfg]
    bridge: Bridge
    start: Callable

    def __init__(self, queue_size: int) -> None: ...
    @property
    def assets(self) -> Optional[FilePath]: ...
    @assets.setter
    def assets(self, value: FilePath) -> None: ...
    def on_pause(self): ...
    def on_resume(self): ...
    def on_dispose(self): ...
    def on_refresh(self): ...


class UiPluginType(PluginType, Protocol):
    pages: dict[str, PageType]
    def on_start(self): ...


class DataPluginType(PluginType, Protocol):
    def on_contribute(self): ...
