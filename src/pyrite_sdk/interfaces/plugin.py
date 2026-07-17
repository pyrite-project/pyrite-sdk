from __future__ import annotations
from typing import Protocol, runtime_checkable, Callable, TYPE_CHECKING
from ..interfaces.ui import PageType

if TYPE_CHECKING:
    from ..core.bridge import Bridge

@runtime_checkable
class PluginType(Protocol):
    bridge: Bridge
    start: Callable

    def __init__(self, queue_size: int) -> None: ...
    def on_pause(self): ...
    def on_resume(self): ...
    def on_dispose(self): ...
    def on_refresh(self): ...


class UiPluginType(PluginType, Protocol):
    pages: dict[str, PageType]
    def on_start(self): ...


class DataPluginType(PluginType, Protocol):
    def on_contribute(self): ...
