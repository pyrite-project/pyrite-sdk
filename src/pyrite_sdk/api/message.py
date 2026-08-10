from __future__ import annotations

from typing import Any, Callable, Optional, TYPE_CHECKING

from ..models.schema import request

if TYPE_CHECKING:
    from ..core.bridge import Bridge


class Message:
    def __init__(self, bridge: Bridge) -> None:
        self._bridge = bridge

    def show(
        self,
        message: str,
        type: str = "info",
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._bridge.push_wait_response(
            request("sdk.message.show", payload={"type": type, "message": message}),
            callback=callback,
        )

    def info(
        self, message: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self.show(message, "info", callback)

    def success(
        self, message: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self.show(message, "success", callback)

    def warning(
        self, message: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self.show(message, "warning", callback)

    def error(
        self, message: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self.show(message, "error", callback)
