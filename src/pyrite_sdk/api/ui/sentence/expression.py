from __future__ import annotations

from ....utils.ui import RFWSerializable, _serialize_value, raw
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


class RFWData(RFWSerializable):
    def __init__(self, value: Any, data_value: Any = None) -> None:
        self.value = value
        self.data_value = value if data_value is None else data_value

    def to_rfw(self) -> str:
        return _serialize_value(self.value)

    def to_data(self) -> Any:
        from ....utils.ui import to_data

        return to_data(self.data_value)


class RFWLiteral(RFWSerializable):
    def __init__(self, rfw_value: str, data_value: Any) -> None:
        self.rfw_value = rfw_value
        self.data_value = data_value

    def to_rfw(self) -> str:
        return self.rfw_value

    def to_data(self) -> Any:
        return self.data_value


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


def ternary(condition: Any, when_true: Any, when_false: Any) -> SwitchExpr:
    if isinstance(condition, ComparisonExpr):
        return condition.to_switch(when_true, when_false)
    return SwitchExpr(condition, {True: when_true}, default=when_false)


class _IconNamespace:
    _codes: dict[str, int] = {
        "add": 0xE047,
        "arrow_back": 0xE092,
        "chevron_right": 0xE15F,
        "info_outline": 0xE33D,
        "person": 0xE491,
        "search": 0xE567,
        "widgets": 0xE6E6,
    }

    def __getattr__(self, key: str) -> RFWData:
        if key not in self._codes:
            raise AttributeError(
                f"Unknown Material icon {key!r}; use icon_data(code_point) for custom icons"
            )
        return icon_data(self._codes[key])


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
    center = RFWData({"x": RFWLiteral("0.0", 0.0), "y": RFWLiteral("0.0", 0.0)})
    center_left = RFWData({"x": RFWLiteral("-1.0", -1.0), "y": RFWLiteral("0.0", 0.0)})
    center_right = RFWData({"x": RFWLiteral("1.0", 1.0), "y": RFWLiteral("0.0", 0.0)})
    top_left = RFWData({"x": RFWLiteral("-1.0", -1.0), "y": RFWLiteral("-1.0", -1.0)})
    top_center = RFWData({"x": RFWLiteral("0.0", 0.0), "y": RFWLiteral("-1.0", -1.0)})
    top_right = RFWData({"x": RFWLiteral("1.0", 1.0), "y": RFWLiteral("-1.0", -1.0)})
    bottom_left = RFWData({"x": RFWLiteral("-1.0", -1.0), "y": RFWLiteral("1.0", 1.0)})
    bottom_center = RFWData({"x": RFWLiteral("0.0", 0.0), "y": RFWLiteral("1.0", 1.0)})
    bottom_right = RFWData({"x": RFWLiteral("1.0", 1.0), "y": RFWLiteral("1.0", 1.0)})

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
    _aliases: dict[str, str] = {
        "normal": "w400",
        "bold": "w700",
    }

    def __getattr__(self, key: str) -> RFWSerializable:
        value = self._aliases.get(key, _kwarg_name(key))
        return RFWLiteral(_serialize_value(value), value)


Icons = _IconNamespace()
Colors = _ColorNamespace()
EdgeInsets = _EdgeInsetsNamespace()
Alignment = _AlignmentNamespace()
Border = _BorderNamespace()
BorderRadius = _BorderRadiusNamespace()
BoxDecoration = _BoxDecorationNamespace()
Radius = _RadiusNamespace()
TextStyle = _TextStyleNamespace()
FontWeight = _FontWeightNamespace()
FontStyle = _EnumNamespace()
MainAxisAlignment = _EnumNamespace()
CrossAxisAlignment = _EnumNamespace()
MainAxisSize = _EnumNamespace()
TextAlign = _EnumNamespace()
TextDirection = _EnumNamespace()
Axis = _EnumNamespace()
BoxFit = _EnumNamespace()
Clip = _EnumNamespace()
