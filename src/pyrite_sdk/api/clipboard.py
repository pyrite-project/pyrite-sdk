from __future__ import annotations

from typing import Any, Callable, Optional, TYPE_CHECKING

from ..models.schema import request

if TYPE_CHECKING:
    from ..core.bridge import Bridge


class Clipboard:
    def __init__(self, bridge: Bridge) -> None:
        self._bridge = bridge

    def set_text(
        self, text: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._bridge.push_wait_response(
            request("sdk.clipboard.set_text", payload={"text": text}),
            callback=callback,
        )
