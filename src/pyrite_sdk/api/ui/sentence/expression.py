from __future__ import annotations

from ....utils.ui import RFWSerializable, _serialize_value
from ._material_icons import (
    MATERIAL_ICON_CODES,
    MATERIAL_ICON_MATCH_TEXT_DIRECTION,
    _MaterialIconNamespaceHints,
)
from ._rfw_types import RFWData, RFWLiteral
from typing import Any


class Expr(RFWSerializable):
    __hash__ = object.__hash__

    def __init__(self, value: str) -> None:
        self._value: str = value

    def __str__(self) -> str:
        return self.to_rfw()

    def __bool__(self) -> bool:
        raise TypeError("RFW expressions cannot be evaluated as Python booleans")

    def to_rfw(self) -> str:
        return self._value

    def _unsupported(self, operator: str) -> "Expr":
        raise TypeError(f'RFW text libraries do not support "{operator}" expressions')

    def __add__(self, other: Any) -> "Expr":
        return self._unsupported("+")

    def __radd__(self, other: Any) -> "Expr":
        return self._unsupported("+")

    def __sub__(self, other: Any) -> "Expr":
        return self._unsupported("-")

    def __rsub__(self, other: Any) -> "Expr":
        return self._unsupported("-")

    def __mul__(self, other: Any) -> "Expr":
        return self._unsupported("*")

    def __rmul__(self, other: Any) -> "Expr":
        return self._unsupported("*")

    def __truediv__(self, other: Any) -> "Expr":
        return self._unsupported("/")

    def __rtruediv__(self, other: Any) -> "Expr":
        return self._unsupported("/")

    def __mod__(self, other: Any) -> "Expr":
        return self._unsupported("%")

    def __rmod__(self, other: Any) -> "Expr":
        return self._unsupported("%")

    def __eq__(self, other: Any) -> "Expr":  # type: ignore[override]
        return self.eq(other)

    def __ne__(self, other: Any) -> "Expr":  # type: ignore[override]
        return self.ne(other)

    def __lt__(self, other: Any) -> "Expr":
        return ComparisonExpr(self, "<", other)

    def __le__(self, other: Any) -> "Expr":
        return ComparisonExpr(self, "<=", other)

    def __gt__(self, other: Any) -> "Expr":
        return ComparisonExpr(self, ">", other)

    def __ge__(self, other: Any) -> "Expr":
        return ComparisonExpr(self, ">=", other)

    def __and__(self, other: Any) -> "Expr":
        return self._unsupported("&&")

    def __rand__(self, other: Any) -> "Expr":
        return self._unsupported("&&")

    def __or__(self, other: Any) -> "Expr":
        return self._unsupported("||")

    def __ror__(self, other: Any) -> "Expr":
        return self._unsupported("||")

    def __invert__(self) -> "Expr":
        return self.not_()

    def eq(self, other: Any) -> "Expr":
        return ComparisonExpr(self, "==", other)

    def ne(self, other: Any) -> "Expr":
        return ComparisonExpr(self, "!=", other)

    def lt(self, other: Any) -> "Expr":
        return ComparisonExpr(self, "<", other)

    def le(self, other: Any) -> "Expr":
        return ComparisonExpr(self, "<=", other)

    def gt(self, other: Any) -> "Expr":
        return ComparisonExpr(self, ">", other)

    def ge(self, other: Any) -> "Expr":
        return ComparisonExpr(self, ">=", other)

    def and_(self, other: Any) -> "Expr":
        return self._unsupported("&&")

    def or_(self, other: Any) -> "Expr":
        return self._unsupported("||")

    def not_(self) -> "Expr":
        return SwitchExpr(self, {True: False}, default=True)


class ComparisonExpr(Expr):
    def __init__(self, left: Any, operator: str, right: Any) -> None:
        self.left = left
        self.operator = operator
        self.right = right
        super().__init__("")

    def to_switch(self, when_true: Any, when_false: Any) -> "SwitchExpr":
        if self.operator == "==":
            return SwitchExpr(self.left, {self.right: when_true}, default=when_false)
        if self.operator == "!=":
            return SwitchExpr(self.left, {self.right: when_false}, default=when_true)
        if not isinstance(self.right, int) or isinstance(self.right, bool) or self.right < 0:
            raise TypeError(
                f'RFW cannot serialize "{self.operator}" for non-negative integer switch lowering'
            )
        if self.right > 100:
            raise ValueError("RFW switch lowering refuses to expand more than 100 numeric cases")
        if self.operator == ">":
            return SwitchExpr(self.left, {value: when_false for value in range(self.right + 1)}, default=when_true)
        if self.operator == ">=":
            return SwitchExpr(self.left, {value: when_false for value in range(self.right)}, default=when_true)
        if self.operator == "<":
            return SwitchExpr(self.left, {value: when_true for value in range(self.right)}, default=when_false)
        if self.operator == "<=":
            return SwitchExpr(self.left, {value: when_true for value in range(self.right + 1)}, default=when_false)
        raise TypeError(f'RFW cannot serialize "{self.operator}" comparisons')

    def to_rfw(self) -> str:
        return self.to_switch(True, False).to_rfw()


class SwitchExpr(Expr):
    def __init__(self, value: Any, cases: dict[Any, Any], default: Any = None) -> None:
        self.value = value
        self.cases = cases
        self.default = default
        super().__init__("")

    def to_rfw(self) -> str:
        entries = [
            f"{_serialize_value(key)}: {_serialize_value(value)}"
            for key, value in self.cases.items()
        ]
        if self.default is not None:
            entries.append(f"default: {_serialize_value(self.default)}")
        return f"switch {_serialize_value(self.value)} {{ {', '.join(entries)} }}"


class Ref(Expr):
    def __init__(self, *parts: str) -> None:
        self.parts: tuple[str, ...] = tuple(map(str, parts))
        super().__init__(".".join(self.parts))

    def __getattr__(self, key: str) -> "Ref":
        return Ref(*self.parts, key)

    def __call__(self, *args: Any, **kwargs: Any) -> Expr:
        return call(self, *args, **kwargs)


def expr(value: Any) -> Expr:
    if isinstance(value, Expr):
        return value
    if isinstance(value, RFWSerializable):
        return Expr(value.to_rfw())
    return Expr(str(value))


def ref(*parts: str) -> Ref:
    return Ref(*parts)


def _kwarg_name(name: str) -> str:
    name = name[:-1] if name.endswith("_") else name
    parts = name.split("_")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])


def _filter_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {_kwarg_name(key): value for key, value in kwargs.items() if value is not None}


def _as_double(value: Any) -> Any:
    if isinstance(value, int) and not isinstance(value, bool):
        return RFWLiteral(f"{value}.0", float(value))
    return value


def _rfw_map(**kwargs: Any) -> RFWData:
    return RFWData(_filter_kwargs(kwargs))


def call(name: str | RFWSerializable, *args: Any, **kwargs: Any) -> Expr:
    rendered_name = name.to_rfw() if isinstance(name, RFWSerializable) else str(name)
    if rendered_name == "Duration":
        milliseconds = kwargs.get("milliseconds", 0)
        milliseconds += kwargs.get("seconds", 0) * 1000
        milliseconds += kwargs.get("minutes", 0) * 60 * 1000
        milliseconds += kwargs.get("hours", 0) * 60 * 60 * 1000
        return Expr(str(milliseconds))
    if rendered_name == "InputDecoration":
        return _rfw_map(**kwargs)
    rendered_args = [_serialize_value(arg) for arg in args]
    rendered_args.extend(
        f"{_kwarg_name(key)}: {_serialize_value(value)}"
        for key, value in kwargs.items()
        if value is not None
    )
    return Expr(f"{rendered_name}({', '.join(rendered_args)})")


def input_decoration(
    *args,
    label_text: str | None = None,
    hint_text: str | None = None,
    helper_text: str | None = None,
    error_text: str | None = None,
    prefix_text: str | None = None,
    suffix_text: str | None = None,
    prefix_icon: Any = None,
    suffix_icon: Any = None,
    is_dense: bool | None = None,
    **kwargs
) -> RFWData:
    return _rfw_map(
        *args,
        label_text=label_text,
        hint_text=hint_text,
        helper_text=helper_text,
        error_text=error_text,
        prefix_text=prefix_text,
        suffix_text=suffix_text,
        prefix_icon=prefix_icon,
        suffix_icon=suffix_icon,
        is_dense=is_dense,
        **kwargs
    )

def button_style(
    foreground_color: RFWSerializable | None = None,
    background_color: RFWSerializable | None = None,
    disabled_foreground_color: RFWSerializable | None = None,
    disabled_background_color: RFWSerializable | None = None,
    shadow_color: RFWSerializable | None = None,
    surface_tint_color: RFWSerializable | None = None,
    elevation: float | int | None = None,
    text_style: RFWData | None = None,
    padding: RFWData | None = None,
    minimum_size: list[float | int] | None = None,
    fixed_size: list[float | int] | None = None,
    maximum_size: list[float | int] | None = None,
    **kwargs
):
    style = {}
    if foreground_color:
        style["foregroundColor"] = foreground_color
    if background_color:
        style["backgroundColor"] = background_color
    if disabled_foreground_color:
        style["disabledForegroundColor"] = disabled_foreground_color
    if disabled_background_color:
        style["disabledBackgroundColor"] = disabled_background_color
    if shadow_color:
        style["shadowColor"] = shadow_color
    if surface_tint_color:
        style["surfaceTintColor"] = surface_tint_color
    if elevation:
        style["elevation"] = elevation
    if text_style:
        style["textStyle"] = text_style
    if padding:
        style["padding"] = padding
    if minimum_size:
        style["minimumSize"] = minimum_size
    if fixed_size:
        style["fixedSize"] = fixed_size
    if maximum_size:
        style["maximumSize"] = maximum_size
    for k, v in kwargs.items():
        style[k] = v
    return style



def ternary(condition: Any, when_true: Any, when_false: Any) -> SwitchExpr:
    if isinstance(condition, ComparisonExpr):
        return condition.to_switch(when_true, when_false)
    return SwitchExpr(condition, {True: when_true}, default=when_false)


class _IconNamespace(_MaterialIconNamespaceHints):
    _codes: dict[str, int] = MATERIAL_ICON_CODES
    _match_text_direction: frozenset[str] = MATERIAL_ICON_MATCH_TEXT_DIRECTION

    def __getattr__(self, key: str) -> RFWData:
        if key not in self._codes:
            raise AttributeError(
                f"Unknown Material icon {key!r}; use icon_data(code_point) for custom icons"
            )
        return icon_data(
            self._codes[key],
            match_text_direction=True if key in self._match_text_direction else None,
        )


def icon_data(
    icon: int,
    font_family: str = "MaterialIcons",
    match_text_direction: bool | None = None,
) -> RFWData:
    return _rfw_map(
        icon=RFWLiteral(hex(icon), icon),
        font_family=font_family,
        match_text_direction=match_text_direction,
    )


class _ColorNamespace:
    black: RFWSerializable
    white: RFWSerializable
    red: RFWSerializable
    blue: RFWSerializable
    green: RFWSerializable
    grey: RFWSerializable
    blueGrey: RFWSerializable
    blue_grey: RFWSerializable

    _colors: dict[str, int] = {
        "black": 0xFF000000,
        "white": 0xFFFFFFFF,
        "red": 0xFFF44336,
        "blue": 0xFF2196F3,
        "green": 0xFF4CAF50,
        "grey": 0xFF9E9E9E,
        "blueGrey": 0xFF607D8B,
        "blue_grey": 0xFF607D8B,
    }

    def __getattr__(self, key: str) -> RFWSerializable:
        if key not in self._colors:
            raise AttributeError(f"Unknown Material color {key!r}; use color(value) for custom colors")
        return color(self._colors[key])


def color(value: int) -> RFWSerializable:
    return RFWLiteral(hex(value), value)


class _EdgeInsetsNamespace:
    def all(self, value: Any) -> RFWData:
        return RFWData([_as_double(value)])

    def symmetric(self, vertical: Any = None, horizontal: Any = None) -> RFWData:
        start = _as_double(horizontal if horizontal is not None else 0)
        top = _as_double(vertical if vertical is not None else 0)
        return RFWData([start, top, start, top])

    def only(
        self,
        left: Any = 0,
        top: Any = 0,
        right: Any = 0,
        bottom: Any = 0,
        start: Any = None,
        end: Any = None,
    ) -> RFWData:
        return RFWData([
            _as_double(left if start is None else start),
            _as_double(top),
            _as_double(right if end is None else end),
            _as_double(bottom),
        ])

    def from_steb(self, start: Any, top: Any, end: Any, bottom: Any) -> RFWData:
        return RFWData([_as_double(start), _as_double(top), _as_double(end), _as_double(bottom)])

    def fromLTRB(self, left: Any, top: Any, right: Any, bottom: Any) -> RFWData:
        return self.only(left=left, top=top, right=right, bottom=bottom)


class _AlignmentNamespace:
    center: RFWData = RFWData({"x": RFWLiteral("0.0", 0.0), "y": RFWLiteral("0.0", 0.0)})
    center_left: RFWData = RFWData({"x": RFWLiteral("-1.0", -1.0), "y": RFWLiteral("0.0", 0.0)})
    center_right: RFWData = RFWData({"x": RFWLiteral("1.0", 1.0), "y": RFWLiteral("0.0", 0.0)})
    top_left: RFWData = RFWData({"x": RFWLiteral("-1.0", -1.0), "y": RFWLiteral("-1.0", -1.0)})
    top_center: RFWData = RFWData({"x": RFWLiteral("0.0", 0.0), "y": RFWLiteral("-1.0", -1.0)})
    top_right: RFWData = RFWData({"x": RFWLiteral("1.0", 1.0), "y": RFWLiteral("-1.0", -1.0)})
    bottom_left: RFWData = RFWData({"x": RFWLiteral("-1.0", -1.0), "y": RFWLiteral("1.0", 1.0)})
    bottom_center: RFWData = RFWData({"x": RFWLiteral("0.0", 0.0), "y": RFWLiteral("1.0", 1.0)})
    bottom_right: RFWData = RFWData({"x": RFWLiteral("1.0", 1.0), "y": RFWLiteral("1.0", 1.0)})

    def __call__(self, x: Any, y: Any) -> RFWData:
        return RFWData({"x": _as_double(x), "y": _as_double(y)})

    def directional(self, start: Any, y: Any) -> RFWData:
        return RFWData({"start": _as_double(start), "y": _as_double(y)})


class _RadiusNamespace:
    def circular(self, value: Any) -> RFWData:
        return RFWData({"x": _as_double(value)})

    def elliptical(self, x: Any, y: Any) -> RFWData:
        return RFWData({"x": _as_double(x), "y": _as_double(y)})


class _BorderRadiusNamespace:
    def circular(self, value: Any) -> RFWData:
        return RFWData([Radius.circular(value)])

    def all(self, radius: Any) -> RFWData:
        return RFWData([radius])

    def only(
        self,
        top_left: Any = None,
        top_right: Any = None,
        bottom_left: Any = None,
        bottom_right: Any = None,
        top_start: Any = None,
        top_end: Any = None,
        bottom_start: Any = None,
        bottom_end: Any = None,
    ) -> RFWData:
        return RFWData([
            top_start or top_left or Radius.circular(0),
            top_end or top_right or Radius.circular(0),
            bottom_start or bottom_left or Radius.circular(0),
            bottom_end or bottom_right or Radius.circular(0),
        ])


class _BorderNamespace:
    def side(
        self,
        color: Any = None,
        width: Any = 1,
        style: Any = "solid",
    ) -> RFWData:
        return _rfw_map(color=color, width=_as_double(width), style=style)

    def all(
        self,
        color: Any = None,
        width: Any = 1,
        style: Any = "solid",
    ) -> RFWData:
        return RFWData([self.side(color=color, width=width, style=style)])

    def only(
        self,
        left: Any = None,
        top: Any = None,
        right: Any = None,
        bottom: Any = None,
        start: Any = None,
        end: Any = None,
    ) -> RFWData:
        return RFWData([
            start or left or self.side(width=0),
            top or self.side(width=0),
            end or right or self.side(width=0),
            bottom or self.side(width=0),
        ])


class _BoxDecorationNamespace:
    def __call__(self, **kwargs: Any) -> RFWData:
        return _rfw_map(type="box", **kwargs)


class _TextStyleNamespace:
    def __call__(self, **kwargs: Any) -> RFWData:
        data = _filter_kwargs(kwargs)
        for key in (
            "fontSize",
            "letterSpacing",
            "wordSpacing",
            "height",
            "decorationThickness",
        ):
            if key in data:
                data[key] = _as_double(data[key])
        return RFWData(data)


class _EnumNamespace:
    def __getattr__(self, key: str) -> RFWSerializable:
        value = _kwarg_name(key)
        return RFWLiteral(_serialize_value(value), value)


class _FontWeightNamespace(_EnumNamespace):
    w100: RFWSerializable
    w200: RFWSerializable
    w300: RFWSerializable
    w400: RFWSerializable
    w500: RFWSerializable
    w600: RFWSerializable
    w700: RFWSerializable
    w800: RFWSerializable
    w900: RFWSerializable
    normal: RFWSerializable
    bold: RFWSerializable

    _aliases: dict[str, str] = {
        "normal": "w400",
        "bold": "w700",
    }

    def __getattr__(self, key: str) -> RFWSerializable:
        value = self._aliases.get(key, _kwarg_name(key))
        return RFWLiteral(_serialize_value(value), value)


class _FontStyleNamespace(_EnumNamespace):
    normal: RFWSerializable
    italic: RFWSerializable


class _MainAxisAlignmentNamespace(_EnumNamespace):
    start: RFWSerializable
    end: RFWSerializable
    center: RFWSerializable
    space_between: RFWSerializable
    space_around: RFWSerializable
    space_evenly: RFWSerializable


class _CrossAxisAlignmentNamespace(_EnumNamespace):
    start: RFWSerializable
    end: RFWSerializable
    center: RFWSerializable
    stretch: RFWSerializable
    baseline: RFWSerializable


class _MainAxisSizeNamespace(_EnumNamespace):
    min: RFWSerializable
    max: RFWSerializable


class _TextAlignNamespace(_EnumNamespace):
    left: RFWSerializable
    right: RFWSerializable
    center: RFWSerializable
    justify: RFWSerializable
    start: RFWSerializable
    end: RFWSerializable


class _TextDirectionNamespace(_EnumNamespace):
    rtl: RFWSerializable
    ltr: RFWSerializable


class _AxisNamespace(_EnumNamespace):
    horizontal: RFWSerializable
    vertical: RFWSerializable


class _BoxFitNamespace(_EnumNamespace):
    fill: RFWSerializable
    contain: RFWSerializable
    cover: RFWSerializable
    fit_width: RFWSerializable
    fit_height: RFWSerializable
    none: RFWSerializable
    scale_down: RFWSerializable


class _ClipNamespace(_EnumNamespace):
    none: RFWSerializable
    hard_edge: RFWSerializable
    anti_alias: RFWSerializable
    anti_alias_with_save_layer: RFWSerializable


Icons: _IconNamespace = _IconNamespace()
Colors: _ColorNamespace = _ColorNamespace()
EdgeInsets: _EdgeInsetsNamespace = _EdgeInsetsNamespace()
Alignment: _AlignmentNamespace = _AlignmentNamespace()
Border: _BorderNamespace = _BorderNamespace()
BorderRadius: _BorderRadiusNamespace = _BorderRadiusNamespace()
BoxDecoration: _BoxDecorationNamespace = _BoxDecorationNamespace()
Radius: _RadiusNamespace = _RadiusNamespace()
TextStyle: _TextStyleNamespace = _TextStyleNamespace()
FontWeight: _FontWeightNamespace = _FontWeightNamespace()
FontStyle: _FontStyleNamespace = _FontStyleNamespace()
MainAxisAlignment: _MainAxisAlignmentNamespace = _MainAxisAlignmentNamespace()
CrossAxisAlignment: _CrossAxisAlignmentNamespace = _CrossAxisAlignmentNamespace()
MainAxisSize: _MainAxisSizeNamespace = _MainAxisSizeNamespace()
TextAlign: _TextAlignNamespace = _TextAlignNamespace()
TextDirection: _TextDirectionNamespace = _TextDirectionNamespace()
Axis: _AxisNamespace = _AxisNamespace()
BoxFit: _BoxFitNamespace = _BoxFitNamespace()
Clip: _ClipNamespace = _ClipNamespace()
