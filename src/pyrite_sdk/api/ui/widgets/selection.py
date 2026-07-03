from .base import Widget
from ....interfaces.ui import EventType
from ....utils.ui import DataSerializer, RFWSerializable, _serialize_value, raw
from ..event import Event
from ..sentence import Alignment, BorderRadius, BoxDecoration, Colors, EdgeInsets, TextStyle, ternary
from typing import Any, Optional


def _bind_value(action: Optional[EventType | Any], value: Any) -> Optional[Any]:
    if action is None:
        return None
    if isinstance(action, Event):
        args = dict(action.args)
        args.setdefault("value", value)
        event_name = action.event if getattr(action, "_explicit_event", False) else ""
        return Event(action.callback, args=args, event=event_name)
    if isinstance(action, DataSerializer) and isinstance(action.data, str):
        replacement = _serialize_value(value)
        return raw(action.data.replace("data.value", replacement))
    if isinstance(action, RFWSerializable):
        replacement = _serialize_value(value)
        return raw(action.to_rfw().replace("data.value", replacement))
    return action


def _box(
    *,
    width: float,
    height: float,
    decoration: Any,
    child: Optional[Any] = None,
    alignment: Optional[Any] = None,
    padding: Optional[Any] = None,
) -> Widget:
    return Widget(
        "Container",
        width=width,
        height=height,
        alignment=alignment,
        padding=padding,
        decoration=decoration,
        child=child,
        add_to_parent=False,
    )


class Checkbox(Widget):
    def __init__(
        self,
        value: Optional[Any] = None,
        on_changed: Optional[EventType | Any] = None,
        tristate: Optional[bool] = None,
        active_color: Optional[Any] = None,
        check_color: Optional[Any] = None,
        autofocus: Optional[bool] = None,
        **kwargs: Any
    ) -> None:
        checked = value if value is not None else False
        next_value = ternary(checked, False, True)
        mark = Widget(
            "Text",
            text=ternary(checked, "x", ""),
            style=TextStyle(
                color=check_color or Colors.white,
                font_size=16,
                font_weight="w700",
            ),
            add_to_parent=False,
        )
        child = _box(
            width=24.0,
            height=24.0,
            alignment=Alignment.center,
            decoration=BoxDecoration(
                color=ternary(checked, active_color or Colors.blue, Colors.grey),
                border_radius=BorderRadius.circular(4),
            ),
            child=mark,
        )
        super().__init__("GestureDetector",
                        onTap=_bind_value(on_changed, next_value),
                        child=child,
                        **kwargs)


class Switch(Widget):
    def __init__(
        self,
        value: Optional[Any] = None,
        on_changed: Optional[EventType | Any] = None,
        active_color: Optional[Any] = None,
        active_track_color: Optional[Any] = None,
        inactive_thumb_color: Optional[Any] = None,
        inactive_track_color: Optional[Any] = None,
        autofocus: Optional[bool] = None,
        **kwargs: Any
    ) -> None:
        selected = value if value is not None else False
        next_value = ternary(selected, False, True)
        thumb = _box(
            width=22.0,
            height=22.0,
            decoration=BoxDecoration(
                color=ternary(selected, active_color or Colors.white, inactive_thumb_color or Colors.white),
                border_radius=BorderRadius.circular(11),
            ),
        )
        aligned_thumb = Widget(
            "Align",
            alignment=ternary(selected, Alignment.center_right, Alignment.center_left),
            child=thumb,
            add_to_parent=False,
        )
        child = _box(
            width=48.0,
            height=28.0,
            padding=EdgeInsets.all(3),
            decoration=BoxDecoration(
                color=ternary(selected, active_track_color or Colors.blue, inactive_track_color or Colors.grey),
                border_radius=BorderRadius.circular(14),
            ),
            child=aligned_thumb,
        )
        super().__init__("GestureDetector",
                        onTap=_bind_value(on_changed, next_value),
                        child=child,
                        **kwargs)


class Radio(Widget):
    def __init__(
        self,
        value: Optional[Any] = None,
        group_value: Optional[Any] = None,
        on_changed: Optional[EventType | Any] = None,
        active_color: Optional[Any] = None,
        autofocus: Optional[bool] = None,
        **kwargs: Any
    ) -> None:
        selected = group_value == value if group_value is not None else False
        dot = _box(
            width=12.0,
            height=12.0,
            decoration=BoxDecoration(
                color=ternary(selected, active_color or Colors.blue, Colors.white),
                border_radius=BorderRadius.circular(6),
            ),
        )
        child = _box(
            width=24.0,
            height=24.0,
            alignment=Alignment.center,
            decoration=BoxDecoration(
                color=ternary(selected, Colors.white, Colors.grey),
                border_radius=BorderRadius.circular(12),
            ),
            child=dot,
        )
        super().__init__("GestureDetector",
                        onTap=_bind_value(on_changed, value),
                        child=child,
                        **kwargs)


class Slider(Widget):
    def __init__(
        self,
        value: Optional[Any] = None,
        on_changed: Optional[EventType | Any] = None,
        min: Optional[Any] = None,
        max: Optional[Any] = None,
        divisions: Optional[int] = None,
        label: Optional[Any] = None,
        active_color: Optional[Any] = None,
        inactive_color: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        super().__init__("Slider",
                        value=value,
                        onChanged=on_changed,
                        min=min,
                        max=max,
                        divisions=divisions,
                        label=label,
                        activeColor=active_color,
                        inactiveColor=inactive_color,
                        **kwargs)
