from __future__ import annotations

from pathlib import Path as FilePath
from typing import Any, Callable, Optional, TYPE_CHECKING

from ..models.consts import PathScope
from ..models.schema import PathRequestPayload, request

if TYPE_CHECKING:
    from ..core.bridge import Bridge


class Path:
    def __init__(self, bridge: Bridge) -> None:
        self._bridge = bridge
        context = getattr(bridge, "context", None)
        self._plugin_path = getattr(context, "plugin_dir", None)
        self._data_path = getattr(context, "data_dir", None)
        self._cache_path = getattr(context, "cache_dir", None)
        self._temp_path = getattr(context, "temp_dir", None)

    def get(
        self,
        scope: str | PathScope,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        scope_value = scope.value if isinstance(scope, PathScope) else scope
        self._bridge.push_wait_response(
            request(
                "sdk.path.request",
                payload=PathRequestPayload(scope=scope_value),
            ),
            callback=callback,
        )

    def plugin(self) -> FilePath:
        if self._plugin_path is not None:
            return self._plugin_path
        return self._bridge.request_path(PathScope.PLUGIN)

    def data(self) -> FilePath:
        if self._data_path is not None:
            return self._data_path
        return self._bridge.request_path(PathScope.DATA)

    def cache(self) -> FilePath:
        if self._cache_path is not None:
            return self._cache_path
        return self._bridge.request_path(PathScope.CACHE)

    def temp(self) -> FilePath:
        if self._temp_path is not None:
            return self._temp_path
        return self._bridge.request_path(PathScope.TEMP)
