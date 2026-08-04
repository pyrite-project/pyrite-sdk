from __future__ import annotations

from typing import Callable, Optional, TYPE_CHECKING

from ..models.schema import request

if TYPE_CHECKING:
    from ..core.bridge import Bridge


class Clipboard:
    def __init__(self, bridge: Bridge):
        self._bridge = bridge

    def set_text(self, text: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request("sdk.clipboard.set_text", payload={"text": text}),
            callback=callback,
        )
