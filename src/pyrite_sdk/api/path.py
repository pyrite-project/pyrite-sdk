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
        value = os.environ.get("PYRITE_IDE_PLUGIN_DIR")
        if value:
            return FilePath(value)
        return self._bridge.request_path(PathScope.PLUGIN)

    def data(self) -> FilePath:
        value = os.environ.get("PYRITE_IDE_PLUGIN_DATA_DIR")
        if value:
            return FilePath(value)
        return self._bridge.request_path(PathScope.DATA)

    def cache(self) -> FilePath:
        value = os.environ.get("PYRITE_IDE_PLUGIN_CACHE_DIR")
        if value:
            return FilePath(value)
        return self._bridge.request_path(PathScope.CACHE)

    def temp(self) -> FilePath:
        value = os.environ.get("PYRITE_IDE_PLUGIN_TEMP_DIR")
        if value:
            return FilePath(value)
        return self._bridge.request_path(PathScope.TEMP)
