from __future__ import annotations

from pathlib import PurePosixPath
from urllib.parse import quote


class PluginResource(str):
    """Plugin-scoped, read-only resource below the package assets directory."""

    def __new__(cls, path: str) -> "PluginResource":
        normalized = path.replace("\\", "/")
        parts = PurePosixPath(normalized).parts
        if (
            not normalized.startswith("assets/")
            or normalized.startswith("/")
            or ".." in parts
            or "\x00" in normalized
            or normalized != path
        ):
            raise ValueError("Plugin resources must be relative paths below assets/")
        value = str.__new__(cls, "plugin-resource:///" + quote(normalized, safe="/"))
        value.path = normalized
        return value

    path: str


class Resources:
    def asset(self, path: str) -> PluginResource:
        return PluginResource(path)

    def uri(self, path: str) -> str:
        return str(self.asset(path))


__all__ = ["PluginResource", "Resources"]
