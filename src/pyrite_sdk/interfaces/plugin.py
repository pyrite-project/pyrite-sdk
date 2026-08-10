from __future__ import annotations
from typing import Any, Callable, Protocol, TYPE_CHECKING, runtime_checkable

if TYPE_CHECKING:
    from ..core.bridge import Bridge


@runtime_checkable
class PluginType(Protocol):
    bridge: Bridge
    start: Callable[..., Any]

    def __init__(self, queue_size: int) -> None: ...
    def on_pause(self) -> Any: ...
    def on_resume(self) -> Any: ...
    def on_dispose(self) -> Any: ...


class UiPluginType(PluginType, Protocol):
    def on_start(self) -> Any: ...


class DataPluginType(PluginType, Protocol):
    def on_contribute(self) -> Any: ...
