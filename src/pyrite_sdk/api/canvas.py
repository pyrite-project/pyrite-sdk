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

from typing import Any, Optional

from .resources import PluginResource


def _compact(mapping: dict) -> dict:
    """Returns [mapping] with ``None`` values removed, order preserved."""
    return {key: value for key, value in mapping.items() if value is not None}


def _flatten_points(points) -> list:
    """Accepts a flat ``[x0, y0, ...]`` list or ``[(x, y), ...]`` pairs."""
    flat: list = []
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

    primary = "theme:primary"
    on_primary = "theme:onPrimary"
    secondary = "theme:secondary"
    on_secondary = "theme:onSecondary"
    surface = "theme:surface"
    on_surface = "theme:onSurface"
    on_surface_variant = "theme:onSurfaceVariant"
    surface_container_highest = "theme:surfaceContainerHighest"
    outline = "theme:outline"
    error = "theme:error"
    on_error = "theme:onError"

    def __call__(self, value: str) -> str:
        return str(value)

    def theme(self, role: str) -> str:
        return f"theme:{role}"


#: Both ``Color`` and ``color`` produce a color token string.
Color = _Color()
color = Color


# -- Gradients ----------------------------------------------------------------


def linear_gradient(
    frm, to, colors, stops=None, tile_mode=None
) -> dict:
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
    center, radius, colors, stops=None, focal=None, tile_mode=None
) -> dict:
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
    color=None,
    stroke_width=None,
    style=None,
    stroke_cap=None,
    stroke_join=None,
    opacity=None,
    blend_mode=None,
    shader=None,
    anti_alias=None,
) -> dict:
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


def line(x1, y1, x2, y2, *, paint, id=None) -> dict:
    return _compact(
        {"op": "line", "x1": x1, "y1": y1, "x2": x2, "y2": y2, "id": id, "paint": paint}
    )


def polyline(points, *, paint, id=None) -> dict:
    return _compact(
        {"op": "polyline", "points": _flatten_points(points), "id": id, "paint": paint}
    )


def rect(x, y, w, h, *, paint, id=None) -> dict:
    return _compact(
        {"op": "rect", "x": x, "y": y, "w": w, "h": h, "id": id, "paint": paint}
    )


def rrect(
    x, y, w, h, *, paint, radius=None, rx=None, ry=None, id=None
) -> dict:
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


def circle(cx, cy, r, *, paint, id=None) -> dict:
    return _compact(
        {"op": "circle", "cx": cx, "cy": cy, "r": r, "id": id, "paint": paint}
    )


def oval(x, y, w, h, *, paint, id=None) -> dict:
    return _compact(
        {"op": "oval", "x": x, "y": y, "w": w, "h": h, "id": id, "paint": paint}
    )


def arc(
    x,
    y,
    w,
    h,
    start_angle,
    sweep_angle,
    *,
    paint,
    use_center=None,
    id=None,
) -> dict:
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


def points(mode, points, *, paint, id=None) -> dict:
    return _compact(
        {
            "op": "points",
            "mode": mode,
            "points": _flatten_points(points),
            "id": id,
            "paint": paint,
        }
    )


def polygon(points, *, paint, closed=None, id=None) -> dict:
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


def move_to(x, y) -> dict:
    return {"c": "moveTo", "x": x, "y": y}


def line_to(x, y) -> dict:
    return {"c": "lineTo", "x": x, "y": y}


def quad_to(x1, y1, x, y) -> dict:
    return {"c": "quadTo", "x1": x1, "y1": y1, "x": x, "y": y}


def cubic_to(x1, y1, x2, y2, x, y) -> dict:
    return {"c": "cubicTo", "x1": x1, "y1": y1, "x2": x2, "y2": y2, "x": x, "y": y}


def close() -> dict:
    return {"c": "close"}


def path(commands, *, paint, fill_rule=None, id=None) -> dict:
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
    x,
    y,
    value,
    *,
    size=None,
    family=None,
    weight=None,
    italic=None,
    color=None,
    align=None,
    max_width=None,
    id=None,
) -> dict:
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
    x,
    y,
    *,
    width=None,
    height=None,
    src_x=None,
    src_y=None,
    src_w=None,
    src_h=None,
    opacity=None,
    id=None,
) -> dict:
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


def clip_rect(x, y, w, h, *, anti_alias=None) -> dict:
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


def clip_rrect(x, y, w, h, radius, *, anti_alias=None) -> dict:
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


def clip_path(commands, *, fill_rule=None, anti_alias=None) -> dict:
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


def save() -> dict:
    return {"op": "save"}


def restore() -> dict:
    return {"op": "restore"}


def save_layer(*, bounds=None, opacity=None) -> dict:
    return _compact(
        {
            "op": "saveLayer",
            "bounds": list(bounds) if bounds is not None else None,
            "opacity": opacity,
        }
    )


def group(*ops, opacity=None, transform=None, clip=None) -> dict:
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


def translate(dx, dy) -> dict:
    return {"op": "translate", "dx": dx, "dy": dy}


def scale(sx, sy=None) -> dict:
    return _compact({"op": "scale", "sx": sx, "sy": sy})


def rotate(radians, px=None, py=None) -> dict:
    return _compact({"op": "rotate", "radians": radians, "px": px, "py": py})


def matrix(*, affine=None, m4=None) -> dict:
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
