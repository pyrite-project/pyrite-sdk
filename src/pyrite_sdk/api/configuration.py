from __future__ import annotations

import inspect
from typing import Any, Awaitable, Callable, Mapping, Optional, TYPE_CHECKING

from ..models.schema import request

if TYPE_CHECKING:
    from ..core.bridge import Bridge
    from .events import PluginEventBus, Subscription

ConfigurationHandler = Callable[
    [Mapping[str, Any]],
    Optional[Awaitable[None]],
]


class Configuration:
    """Read and update Manifest-declared configuration values."""

    def __init__(self, bridge: "Bridge", events: "PluginEventBus") -> None:
        self._bridge = bridge
        self._events = events

    def get(
        self,
        configuration_id: str,
        *,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.configuration.get",
                payload={"id": configuration_id},
            ),
            callback=callback,
        )

    def set(
        self,
        configuration_id: str,
        value: Any,
        *,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.configuration.set",
                payload={"id": configuration_id, "value": value},
            ),
            callback=callback,
        )

    def list(self, *, callback: Optional[Callable[..., Any]] = None) -> None:
        self._bridge.push_wait_response(
            request("sdk.configuration.list", payload={}),
            callback=callback,
        )

    def on_changed(
        self,
        handler: ConfigurationHandler,
        *,
        configuration_id: Optional[str] = None,
    ) -> "Subscription":
        plugin_id = getattr(getattr(self._bridge, "context", None), "id", None)

        def _wrapped(events: list[Mapping[str, Any]]) -> Optional[Awaitable[None]]:
            for event in events:
                if configuration_id is not None and event.get("id") != configuration_id:
                    continue
                if plugin_id is not None and event.get("pluginId") not in (
                    None,
                    plugin_id,
                ):
                    continue
                result = handler(event)
                if inspect.isawaitable(result):
                    return result
            return None

        filter_payload: dict[str, Any] = {}
        if plugin_id is not None:
            filter_payload["pluginId"] = plugin_id
        if configuration_id is not None:
            filter_payload["id"] = configuration_id
        return self._events.subscribe(
            "configuration.changed",
            _wrapped,
            filter=filter_payload or None,
            delivery="latest",
        )
