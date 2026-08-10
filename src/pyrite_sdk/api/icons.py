from __future__ import annotations

from .material_icons import (
    MATERIAL_ICON_CODES,
    _MaterialIconNamespaceHints,
)


class MaterialIcon(str):
    """Typed reference to one Flutter Material icon."""

    def __new__(cls, name: str) -> "MaterialIcon":
        if name not in MATERIAL_ICON_CODES:
            raise ValueError(f"Unknown Flutter Material icon: {name}")
        value = str.__new__(cls, f"material:{name}")
        value.name = name
        return value

    name: str


class _MaterialIcons(_MaterialIconNamespaceHints):
    def __getattr__(self, name: str) -> MaterialIcon:
        try:
            return MaterialIcon(name)
        except ValueError as error:
            raise AttributeError(str(error)) from error


Icons = _MaterialIcons()

__all__ = ["Icons", "MaterialIcon"]
