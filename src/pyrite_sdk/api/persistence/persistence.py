from __future__ import annotations
from typing import Any, Callable, Optional, TYPE_CHECKING
from ...models.schema import (
    request,
    PersistenceGetPayload,
    PersistenceSetPayload,
    PersistenceDeletePayload,
    PersistenceListKeysPayload,
    PersistenceClearPayload,
)
if TYPE_CHECKING:
    from ...core.bridge import Bridge


class Persistence:
    def __init__(self, bridge: Bridge) -> None:
        self._bridge = bridge

    def get(
        self,
        group: str,
        key: str,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.persistence.get",
                payload=PersistenceGetPayload(group=group, key=key),
            ),
            callback=callback,
        )

    def set(
        self,
        group: str,
        key: str,
        value: Any,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.persistence.set",
                payload=PersistenceSetPayload(group=group, key=key, value=value),
            ),
            callback=callback,
        )

    def delete(
        self,
        group: str,
        key: str,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.persistence.delete",
                payload=PersistenceDeletePayload(group=group, key=key),
            ),
            callback=callback,
        )

    def list_groups(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._bridge.push_wait_response(
            request("sdk.persistence.list_groups"),
            callback=callback,
        )

    def list_keys(
        self, group: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.persistence.list_keys",
                payload=PersistenceListKeysPayload(group=group),
            ),
            callback=callback,
        )

    def clear(
        self, group: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.persistence.clear",
                payload=PersistenceClearPayload(group=group),
            ),
            callback=callback,
        )
