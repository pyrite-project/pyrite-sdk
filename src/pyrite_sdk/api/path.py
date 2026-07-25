from __future__ import annotations

import os
from pathlib import Path as FilePath
from typing import Optional, Callable, TYPE_CHECKING

from ..models.consts import PathScope
from ..models.schema import PathRequestPayload, request

if TYPE_CHECKING:
    from ..core.bridge import Bridge


class Path:
    def __init__(self, bridge: Bridge):
        self._bridge = bridge
        self._plugin_path = self._environment_path("PYRITE_IDE_PLUGIN_DIR")
        self._data_path = self._environment_path("PYRITE_IDE_PLUGIN_DATA_DIR")
        self._cache_path = self._environment_path("PYRITE_IDE_PLUGIN_CACHE_DIR")
        self._temp_path = self._environment_path("PYRITE_IDE_PLUGIN_TEMP_DIR")

    @staticmethod
    def _environment_path(name: str) -> Optional[FilePath]:
        value = os.environ.get(name)
        return FilePath(value) if value else None

    def get(self, scope: str | PathScope, callback: Optional[Callable] = None):
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
