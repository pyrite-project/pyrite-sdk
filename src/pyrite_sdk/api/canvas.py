"""Builders for Canvas v2 draw ops.

Each helper returns a plain wire dict matching the frozen Canvas op schema
exactly (``op`` discriminator, camelCase keys, ``None`` values dropped). These
dicts ride either ``Canvas(ops=[...])`` (persistent base layer) or the
:class:`CanvasController` ``push_ops``/``set_ops`` invoke methods (ephemeral
overlay).

Coordinates are content-space logical pixels; angles are radians,
clockwise-positive. Point lists are flat ``[x0, y0, x1, y1, ...]`` arrays;
helpers here also accept a list of ``(x, y)`` pairs and flatten it.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

from .resources import PluginResource


def _compact(mapping: dict[str, Any]) -> dict[str, Any]:
    """Returns [mapping] with ``None`` values removed, order preserved."""
    return {key: value for key, value in mapping.items() if value is not None}


def _flatten_points(points: Iterable[Any]) -> list[Any]:
    """Accepts a flat ``[x0, y0, ...]`` list or ``[(x, y), ...]`` pairs."""
    flat: list[Any] = []
    for point in points:
        if isinstance(point, (list, tuple)):
            flat.extend(point)
        else:
            flat.append(point)
    return flat


# -- Colors -------------------------------------------------------------------


class _Color:
    """Factory for canvas color tokens (hex ``#RRGGBB``/``#AARRGGBB`` or
    ``theme:<role>``). Callable for pass-through; theme roles are attributes."""

    primary: str = "theme:primary"
    on_primary: str = "theme:onPrimary"
    secondary: str = "theme:secondary"
    on_secondary: str = "theme:onSecondary"
    surface: str = "theme:surface"
    on_surface: str = "theme:onSurface"
    on_surface_variant: str = "theme:onSurfaceVariant"
    surface_container_highest: str = "theme:surfaceContainerHighest"
    outline: str = "theme:outline"
    error: str = "theme:error"
    on_error: str = "theme:onError"

    def __call__(self, value: str) -> str:
        return str(value)

    def theme(self, role: str) -> str:
        return f"theme:{role}"


#: Both ``Color`` and ``color`` produce a color token string.
Color: _Color = _Color()
color: _Color = Color


# -- Gradients ----------------------------------------------------------------


def linear_gradient(
    frm: Iterable[Any],
    to: Iterable[Any],
    colors: Iterable[Any],
    stops: Optional[Iterable[Any]] = None,
    tile_mode: Any = None,
) -> dict[str, Any]:
    return _compact(
        {
            "type": "linear",
            "from": list(frm),
            "to": list(to),
            "colors": list(colors),
            "stops": list(stops) if stops is not None else None,
            "tileMode": tile_mode,
        }
    )


def radial_gradient(
    center: Iterable[Any],
    radius: Any,
    colors: Iterable[Any],
    stops: Optional[Iterable[Any]] = None,
    focal: Optional[Iterable[Any]] = None,
    tile_mode: Any = None,
) -> dict[str, Any]:
    return _compact(
        {
            "type": "radial",
            "center": list(center),
            "radius": radius,
            "colors": list(colors),
            "stops": list(stops) if stops is not None else None,
            "focal": list(focal) if focal is not None else None,
            "tileMode": tile_mode,
        }
    )


# -- Paint --------------------------------------------------------------------


def paint(
    *,
    color: Any = None,
    stroke_width: Any = None,
    style: Any = None,
    stroke_cap: Any = None,
    stroke_join: Any = None,
    opacity: Any = None,
    blend_mode: Any = None,
    shader: Any = None,
    anti_alias: Any = None,
) -> dict[str, Any]:
    return _compact(
        {
            "color": color,
            "strokeWidth": stroke_width,
            "style": style,
            "strokeCap": stroke_cap,
            "strokeJoin": stroke_join,
            "opacity": opacity,
            "blendMode": blend_mode,
            "shader": shader,
            "antiAlias": anti_alias,
        }
    )


# -- Geometry -----------------------------------------------------------------


def line(
    x1: Any,
    y1: Any,
    x2: Any,
    y2: Any,
    *,
    paint: dict[str, Any],
    id: Any = None,
) -> dict[str, Any]:
    return _compact(
        {"op": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2, "id": id, "paint": paint}
    )


def polyline(
    points: Iterable[Any], *, paint: dict[str, Any], id: Any = None
) -> dict[str, Any]:
    return _compact(
        {"op": "polyline", "points": _flatten_points(points), "id": id, "paint": paint}
    )


def rect(
    x: Any,
    y: Any,
    w: Any,
    h: Any,
    *,
    paint: dict[str, Any],
    id: Any = None,
) -> dict[str, Any]:
    return _compact(
        {"op": "rect", "x": x, "y": y, "w": w, "h": h, "id": id, "paint": paint}
    )


def rrect(
    x: Any,
    y: Any,
    w: Any,
    h: Any,
    *,
    paint: dict[str, Any],
    radius: Any = None,
    rx: Any = None,
    ry: Any = None,
    id: Any = None,
) -> dict[str, Any]:
    return _compact(
        {
            "op": "rrect",
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "radius": radius,
            "rx": rx,
            "ry": ry,
            "id": id,
            "paint": paint,
        }
    )


def circle(
    cx: Any,
    cy: Any,
    r: Any,
    *,
    paint: dict[str, Any],
    id: Any = None,
) -> dict[str, Any]:
    return _compact(
        {"op": "circle", "cx": cx, "cy": cy, "r": r, "id": id, "paint": paint}
    )


def oval(
    x: Any,
    y: Any,
    w: Any,
    h: Any,
    *,
    paint: dict[str, Any],
    id: Any = None,
) -> dict[str, Any]:
    return _compact(
        {"op": "oval", "x": x, "y": y, "w": w, "h": h, "id": id, "paint": paint}
    )


def arc(
    x: Any,
    y: Any,
    w: Any,
    h: Any,
    start_angle: Any,
    sweep_angle: Any,
    *,
    paint: dict[str, Any],
    use_center: Any = None,
    id: Any = None,
) -> dict[str, Any]:
    return _compact(
        {
            "op": "arc",
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "startAngle": start_angle,
            "sweepAngle": sweep_angle,
            "useCenter": use_center,
            "id": id,
            "paint": paint,
        }
    )


def points(
    mode: Any,
    points: Iterable[Any],
    *,
    paint: dict[str, Any],
    id: Any = None,
) -> dict[str, Any]:
    return _compact(
        {
            "op": "points",
            "mode": mode,
            "points": _flatten_points(points),
            "id": id,
            "paint": paint,
        }
    )


def polygon(
    points: Iterable[Any],
    *,
    paint: dict[str, Any],
    closed: Any = None,
    id: Any = None,
) -> dict[str, Any]:
    return _compact(
        {
            "op": "polygon",
            "points": _flatten_points(points),
            "closed": closed,
            "id": id,
            "paint": paint,
        }
    )


# -- Path ---------------------------------------------------------------------


def move_to(x: Any, y: Any) -> dict[str, Any]:
    return {"c": "moveTo", "x": x, "y": y}


def line_to(x: Any, y: Any) -> dict[str, Any]:
    return {"c": "lineTo", "x": x, "y": y}


def quad_to(x1: Any, y1: Any, x: Any, y: Any) -> dict[str, Any]:
    return {"c": "quadTo", "x1": x1, "y1": y1, "x": x, "y": y}


def cubic_to(
    x1: Any, y1: Any, x2: Any, y2: Any, x: Any, y: Any
) -> dict[str, Any]:
    return {"c": "cubicTo", "x1": x1, "y1": y1, "x2": x2, "y2": y2, "x": x, "y": y}


def close() -> dict[str, Any]:
    return {"c": "close"}


def path(
    commands: Iterable[dict[str, Any]],
    *,
    paint: dict[str, Any],
    fill_rule: Any = None,
    id: Any = None,
) -> dict[str, Any]:
    return _compact(
        {
            "op": "path",
            "commands": list(commands),
            "fillRule": fill_rule,
            "id": id,
            "paint": paint,
        }
    )


# -- Text ---------------------------------------------------------------------


def text(
    x: Any,
    y: Any,
    value: Any,
    *,
    size: Any = None,
    family: Any = None,
    weight: Any = None,
    italic: Any = None,
    color: Any = None,
    align: Any = None,
    max_width: Any = None,
    id: Any = None,
) -> dict[str, Any]:
    return _compact(
        {
            "op": "text",
            "x": x,
            "y": y,
            "text": value,
            "size": size,
            "family": family,
            "weight": weight,
            "italic": italic,
            "color": color,
            "align": align,
            "maxWidth": max_width,
            "id": id,
        }
    )


# -- Image (bitmap bytes are NEVER inlined) -----------------------------------


def image(
    src: PluginResource,
    x: Any,
    y: Any,
    *,
    width: Any = None,
    height: Any = None,
    src_x: Any = None,
    src_y: Any = None,
    src_w: Any = None,
    src_h: Any = None,
    opacity: Any = None,
    id: Any = None,
) -> dict[str, Any]:
    if not isinstance(src, PluginResource):
        raise TypeError("Canvas image sources must use plugin.resources.asset(...)")
    return _compact(
        {
            "op": "image",
            "src": str(src),
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "srcX": src_x,
            "srcY": src_y,
            "srcW": src_w,
            "srcH": src_h,
            "opacity": opacity,
            "id": id,
        }
    )


# -- Clip ---------------------------------------------------------------------


def clip_rect(
    x: Any, y: Any, w: Any, h: Any, *, anti_alias: Any = None
) -> dict[str, Any]:
    return _compact(
        {
            "op": "clip",
            "shape": "rect",
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "antiAlias": anti_alias,
        }
    )


def clip_rrect(
    x: Any,
    y: Any,
    w: Any,
    h: Any,
    radius: Any,
    *,
    anti_alias: Any = None,
) -> dict[str, Any]:
    return _compact(
        {
            "op": "clip",
            "shape": "rrect",
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "radius": radius,
            "antiAlias": anti_alias,
        }
    )


def clip_path(
    commands: Iterable[dict[str, Any]],
    *,
    fill_rule: Any = None,
    anti_alias: Any = None,
) -> dict[str, Any]:
    return _compact(
        {
            "op": "clip",
            "shape": "path",
            "commands": list(commands),
            "fillRule": fill_rule,
            "antiAlias": anti_alias,
        }
    )


# -- Layers -------------------------------------------------------------------


def save() -> dict[str, Any]:
    return {"op": "save"}


def restore() -> dict[str, Any]:
    return {"op": "restore"}


def save_layer(
    *, bounds: Optional[Iterable[Any]] = None, opacity: Any = None
) -> dict[str, Any]:
    return _compact(
        {
            "op": "saveLayer",
            "bounds": list(bounds) if bounds is not None else None,
            "opacity": opacity,
        }
    )


def group(
    *ops: dict[str, Any],
    opacity: Any = None,
    transform: Optional[Iterable[Any]] = None,
    clip: Any = None,
) -> dict[str, Any]:
    return _compact(
        {
            "op": "group",
            "opacity": opacity,
            "transform": list(transform) if transform is not None else None,
            "clip": clip,
            "ops": list(ops),
        }
    )


# -- Transform ----------------------------------------------------------------


def translate(dx: Any, dy: Any) -> dict[str, Any]:
    return {"op": "translate", "dx": dx, "dy": dy}


def scale(sx: Any, sy: Any = None) -> dict[str, Any]:
    return _compact({"op": "scale", "sx": sx, "sy": sy})


def rotate(radians: Any, px: Any = None, py: Any = None) -> dict[str, Any]:
    return _compact({"op": "rotate", "radians": radians, "px": px, "py": py})


def matrix(
    *,
    affine: Optional[Iterable[Any]] = None,
    m4: Any = None,
) -> dict[str, Any]:
    if (affine is None) == (m4 is None):
        raise ValueError("matrix requires exactly one of affine or m4")
    if affine is not None:
        return {"op": "matrix", "affine": list(affine)}
    return {"op": "matrix", "m4": list(m4)}


__all__ = [
    "Color",
    "color",
    "linear_gradient",
    "radial_gradient",
    "paint",
    "line",
    "polyline",
    "rect",
    "rrect",
    "circle",
    "oval",
    "arc",
    "points",
    "polygon",
    "move_to",
    "line_to",
    "quad_to",
    "cubic_to",
    "close",
    "path",
    "text",
    "image",
    "clip_rect",
    "clip_rrect",
    "clip_path",
    "save",
    "restore",
    "save_layer",
    "group",
    "translate",
    "scale",
    "rotate",
    "matrix",
]
