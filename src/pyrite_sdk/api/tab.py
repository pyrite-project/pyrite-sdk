from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, TYPE_CHECKING

from ..models.schema import request

if TYPE_CHECKING:
    from ..core.bridge import Bridge


@dataclass(frozen=True)
class TabViewInstance:
    """A host-allocated instance of a contributed plugin view."""

    plugin_id: str
    session_id: str
    view_id: str
    instance_id: str

    @classmethod
    def from_json(cls, data: dict) -> "TabViewInstance":
        return cls(
            plugin_id=str(data.get("pluginId", "")),
            session_id=str(data.get("sessionId", "")),
            view_id=str(data.get("viewId", "")),
            instance_id=str(data.get("instanceId", "")),
        )


class Tabs:
    """Creates tab placements for views contributed by the current plugin."""

    def __init__(self, bridge: "Bridge") -> None:
        self._bridge = bridge

    def create_view(
        self,
        view_id: str,
        *,
        title: Optional[str] = None,
        expansion: bool = False,
        callback: Optional[Callable] = None,
    ) -> None:
        payload = {"viewId": view_id, "expansion": expansion}
        if title is not None:
            payload["title"] = title

        def _cb(data=None, error=None, **_) -> None:
            if callback is None:
                return
            if error is not None:
                callback(error=error)
                return
            if not isinstance(data, dict):
                callback(error=ValueError("Invalid tab view instance response"))
                return
            instance = TabViewInstance.from_json(data)
            if not instance.instance_id:
                callback(error=ValueError("Tab view response is missing instanceId"))
                return
            callback(instance=instance)

        self._bridge.push_wait_response(
            request("sdk.tab.create_view", payload=payload),
            callback=_cb,
        )
