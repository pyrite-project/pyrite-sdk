from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional, TYPE_CHECKING

from ..models.schema import request

if TYPE_CHECKING:
    from ..core.bridge import Bridge


@dataclass(frozen=True)
class ViewInstanceInfo:
    """Identity returned when the host creates a plugin view instance."""

    plugin_id: str
    session_id: str
    view_id: str
    instance_id: str
    tab_id: Optional[str] = None

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "ViewInstanceInfo":
        return cls(
            plugin_id=str(data.get("pluginId", "")),
            session_id=str(data.get("sessionId", "")),
            view_id=str(data.get("viewId", "")),
            instance_id=str(data.get("instanceId", "")),
            tab_id=data.get("tabId"),
        )


@dataclass(frozen=True)
class EditorTab:
    """Metadata for one tab in the host editor shell."""

    tab_id: str
    index: int
    name: Optional[str]
    kind: str
    placement: str = "editor"
    resource: Optional[str] = None
    plugin_id: Optional[str] = None
    view_id: Optional[str] = None
    view_instance_id: Optional[str] = None

    @property
    def is_plugin_view(self) -> bool:
        return self.kind == "plugin_view"

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "EditorTab":
        view = data.get("view")
        view_data = view if isinstance(view, dict) else {}
        resource = data.get("resource", data.get("path"))
        tab_id = data.get("tabId", data.get("id", resource))
        return cls(
            tab_id=str(tab_id or ""),
            index=int(data.get("index", -1)),
            name=data.get("name"),
            kind=str(data.get("kind", data.get("type", ""))),
            placement=str(data.get("placement", "editor")),
            resource=resource,
            plugin_id=data.get("pluginId", view_data.get("pluginId")),
            view_id=data.get("viewId", view_data.get("viewId")),
            view_instance_id=data.get(
                "viewInstanceId",
                view_data.get("instanceId"),
            ),
        )


class EditorTabs:
    """Controls the host editor shell independently of plugin view content."""

    def __init__(self, bridge: "Bridge") -> None:
        self._bridge = bridge

    def list(self, callback: Optional[Callable[..., Any]] = None) -> None:
        """Lists open editor tabs as ``tabs=list[EditorTab]``."""

        def _cb(data: Any = None, error: Any = None, **_: Any) -> None:
            if callback is None:
                return
            if error is not None:
                callback(error=error)
                return
            if not isinstance(data, list):
                callback(error=ValueError("Invalid editor tab list response"))
                return
            callback(
                tabs=[
                    EditorTab.from_json(item)
                    for item in data
                    if isinstance(item, dict)
                ]
            )

        self._bridge.push_wait_response(
            request("sdk.tab.list"),
            callback=_cb,
        )

    def activate(
        self,
        tab_id: str,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        """Activates a tab by its host-assigned stable id."""
        if not tab_id:
            raise ValueError("tab_id must not be empty")
        self._bridge.push_wait_response(
            request("sdk.tab.activate", payload={"tab_id": tab_id}),
            callback=callback,
        )

    def close(
        self,
        tab_id: str,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        """Closes a tab by its host-assigned stable id."""
        if not tab_id:
            raise ValueError("tab_id must not be empty")
        self._bridge.push_wait_response(
            request("sdk.tab.close", payload={"tab_id": tab_id}),
            callback=callback,
        )
