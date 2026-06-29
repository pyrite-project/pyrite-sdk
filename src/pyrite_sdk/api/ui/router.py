from __future__ import annotations
from typing import TYPE_CHECKING, List
from ...models.schema import request, RouterPushPayload, RouterPopPayload, RouterReplacePayload, RouterGotoPayload

if TYPE_CHECKING:
    from ...core.bridge import Bridge


class Router:
    def __init__(self, bridge: Bridge):
        self._bridge = bridge
        self._stack: List[str] = []
        self._current: str = "home"

    @property
    def current(self) -> str:
        return self._current

    @property
    def stack(self) -> List[str]:
        return self._stack.copy()

    def push(self, page_name: str):
        self._stack.append(self._current)
        self._current = page_name
        self._bridge.push(request("sdk.router.push", RouterPushPayload(page=page_name)))

    def pop(self):
        if len(self._stack) > 0:
            self._current = self._stack.pop()
            self._bridge.push(request("sdk.router.pop", RouterPopPayload()))

    def replace(self, page_name: str):
        self._current = page_name
        self._bridge.push(request("sdk.router.replace", RouterReplacePayload(page=page_name)))

    def goto(self, page_name: str):
        self._stack = ["home"]
        self._current = page_name
        self._bridge.push(request("sdk.router.goto", RouterGotoPayload(page=page_name)))

    def _sync(self, page: str, stack: List[str]):
        self._current = page
        self._stack = stack
