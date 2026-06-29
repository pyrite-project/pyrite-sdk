from __future__ import annotations
from typing import Callable, Optional, Any, TYPE_CHECKING
from ...models.schema import request

if TYPE_CHECKING:
    from ...core.bridge import Bridge


class I18n:
    def __init__(self, bridge: Bridge):
        self._bridge = bridge

    def register(self, locale: str, messages: Any, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.i18n.register",
                payload={"locale": locale, "messages": messages},
            ),
            callback=callback,
        )

    def get(self, locale: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.i18n.get",
                payload={"locale": locale},
            ),
            callback=callback,
        )

    def list(self, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request("sdk.i18n.list"),
            callback=callback,
        )
