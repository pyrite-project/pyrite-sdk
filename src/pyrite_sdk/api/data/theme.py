from __future__ import annotations
from typing import Callable, Optional, Any, TYPE_CHECKING
from ...models.schema import request

if TYPE_CHECKING:
    from ...core.bridge import Bridge


class Theme:
    def __init__(self, bridge: Bridge):
        self._bridge = bridge

    def contribute(self, name: str, data: Any, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.theme.contribute",
                payload={"name": name, "data": data},
            ),
            callback=callback,
        )

    def register_runtime(self, name: str, data: Any, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.theme.register_runtime",
                payload={"name": name, "data": data},
            ),
            callback=callback,
        )

    def revoke(self, name: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request("sdk.theme.revoke", payload={"name": name}),
            callback=callback,
        )

    def get(self, name: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.theme.get",
                payload={"name": name},
            ),
            callback=callback,
        )

    def list(self, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request("sdk.theme.list"),
            callback=callback,
        )
