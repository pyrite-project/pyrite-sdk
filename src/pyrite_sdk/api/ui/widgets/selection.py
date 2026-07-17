from .base import Widget, Var
from ....interfaces.ui import EventType
from typing import Any, Optional


class Checkbox(Widget):
    def __init__(
        self,
        value: Optional[bool] = False,
        on_changed: Optional[EventType | Any] = None,
        tristate: Optional[bool] = None,
        active_color: Optional[Any] = None,
        check_color: Optional[Any] = None,
        focus_color: Optional[Any] = None,
        hover_color: Optional[Any] = None,
        splash_radius: Optional[Any] = None,
        material_tap_target_size: Optional[Any] = None,
        visual_density: Optional[Any] = None,
        autofocus: Optional[bool] = None,
        is_error: Optional[bool] = None,
        semantic_label: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(
            "Checkbox",
            value=value,
            onChanged=on_changed,
            tristate=tristate,
            activeColor=active_color,
            checkColor=check_color,
            focusColor=focus_color,
            hoverColor=hover_color,
            splashRadius=splash_radius,
            materialTapTargetSize=material_tap_target_size,
            visualDensity=visual_density,
            autofocus=autofocus,
            isError=is_error,
            semanticLabel=semantic_label,
            **kwargs
        )
        self.register_callback_binding(False)


class Switch(Widget):
    def __init__(
        self,
        value: Optional[bool] = False,
        on_changed: Optional[EventType | Any] = None,
        active_color: Optional[Any] = None,
        active_thumb_color: Optional[Any] = None,
        active_track_color: Optional[Any] = None,
        inactive_thumb_color: Optional[Any] = None,
        inactive_track_color: Optional[Any] = None,
        focus_color: Optional[Any] = None,
        hover_color: Optional[Any] = None,
        splash_radius: Optional[Any] = None,
        material_tap_target_size: Optional[Any] = None,
        autofocus: Optional[bool] = None,
        padding: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(
            "Switch",
            value=value,
            onChanged=on_changed,
            activeColor=active_color,
            activeThumbColor=active_thumb_color,
            activeTrackColor=active_track_color,
            inactiveThumbColor=inactive_thumb_color,
            inactiveTrackColor=inactive_track_color,
            focusColor=focus_color,
            hoverColor=hover_color,
            splashRadius=splash_radius,
            materialTapTargetSize=material_tap_target_size,
            autofocus=autofocus,
            padding=padding,
            **kwargs
        )
        self.register_callback_binding(False)

class RadioGroup(Widget):
    def __init__(
        self,
        group_value: Optional[str] = "",
        on_changed: Optional[EventType | Any] = None,
        items: Optional[list[dict]] = None,
        enabled: Optional[bool] = None,
        toggleable: Optional[bool] = None,
        active_color: Optional[Any] = None,
        hover_color: Optional[Any] = None,
        splash_radius: Optional[Any] = None,
        material_tap_target_size: Optional[Any] = None,
        dense: Optional[bool] = None,
        selected: Optional[bool] = None,
        control_affinity: Optional[Any] = None,
        autofocus: Optional[bool] = None,
        content_padding: Optional[Any] = None,
        visual_density: Optional[Any] = None,
        enable_feedback: Optional[bool] = None,
        horizontal_title_gap: Optional[Any] = None,
        min_vertical_padding: Optional[Any] = None,
        min_leading_width: Optional[Any] = None,
        min_tile_height: Optional[Any] = None,
        radio_scale_factor: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(
            "RadioGroup",
            groupValue=group_value,
            onChanged=on_changed,
            items=items or [],
            enabled=enabled,
            toggleable=toggleable,
            activeColor=active_color,
            hoverColor=hover_color,
            splashRadius=splash_radius,
            materialTapTargetSize=material_tap_target_size,
            dense=dense,
            selected=selected,
            controlAffinity=control_affinity,
            autofocus=autofocus,
            contentPadding=content_padding,
            visualDensity=visual_density,
            enableFeedback=enable_feedback,
            horizontalTitleGap=horizontal_title_gap,
            minVerticalPadding=min_vertical_padding,
            minLeadingWidth=min_leading_width,
            minTileHeight=min_tile_height,
            radioScaleFactor=radio_scale_factor,
            **kwargs
        )
        default = ""
        if items:
            default = items[0]['value']
        self.register_callback_binding(default, "groupValue")


class Slider(Widget):
    def __init__(
        self,
        value: Optional[Any] = None,
        on_changed: Optional[EventType | Any] = None,
        min: Optional[Any] = None,
        max: Optional[Any] = None,
        divisions: Optional[int] = None,
        label: Optional[Any] = None,
        secondary_track_value: Optional[Any] = None,
        on_change_start: Optional[EventType | Any] = None,
        on_change_end: Optional[EventType | Any] = None,
        active_color: Optional[Any] = None,
        inactive_color: Optional[Any] = None,
        secondary_active_color: Optional[Any] = None,
        thumb_color: Optional[Any] = None,
        autofocus: Optional[bool] = None,
        padding: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(
            "Slider",
            value=value,
            secondaryTrackValue=secondary_track_value,
            onChanged=on_changed,
            onChangeStart=on_change_start,
            onChangeEnd=on_change_end,
            min=min,
            max=max,
            divisions=divisions,
            label=label,
            activeColor=active_color,
            inactiveColor=inactive_color,
            secondaryActiveColor=secondary_active_color,
            thumbColor=thumb_color,
            autofocus=autofocus,
            padding=padding,
            **kwargs
        )
        self.register_callback_binding(0)


class DropdownButton(Widget):
    def __init__(
        self,
        items: Optional[list[dict[str, Any]]] = None,
        value: Optional[Any] = None,
        on_changed: Optional[EventType | Any] = None,
        on_tap: Optional[EventType] = None,
        hint: Optional[Any] = None,
        disabled_hint: Optional[Any] = None,
        elevation: Optional[Any] = None,
        style: Optional[Any] = None,
        underline: Optional[Any] = None,
        icon: Optional[Any] = None,
        icon_size: Optional[Any] = None,
        icon_enabled_color: Optional[Any] = None,
        icon_disabled_color: Optional[Any] = None,
        is_dense: Optional[bool] = None,
        is_expanded: Optional[bool] = None,
        item_height: Optional[Any] = None,
        menu_width: Optional[Any] = None,
        focus_color: Optional[Any] = None,
        autofocus: Optional[bool] = None,
        dropdown_color: Optional[Any] = None,
        menu_max_height: Optional[Any] = None,
        enable_feedback: Optional[bool] = None,
        alignment: Optional[Any] = None,
        border_radius: Optional[Any] = None,
        padding: Optional[Any] = None,
        barrier_dismissible: Optional[bool] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(
            "DropdownButton",
            items=items or [],
            value=value,
            onChanged=on_changed,
            onTap=on_tap,
            hint=hint,
            disabledHint=disabled_hint,
            elevation=elevation,
            style=style,
            underline=underline,
            icon=icon,
            iconSize=icon_size,
            iconEnabledColor=icon_enabled_color,
            iconDisabledColor=icon_disabled_color,
            isDense=is_dense,
            isExpanded=is_expanded,
            itemHeight=item_height,
            menuWidth=menu_width,
            focusColor=focus_color,
            autofocus=autofocus,
            dropdownColor=dropdown_color,
            menuMaxHeight=menu_max_height,
            enableFeedback=enable_feedback,
            alignment=alignment,
            borderRadius=border_radius,
            padding=padding,
            barrierDismissible=barrier_dismissible,
            **kwargs
        )
        default = items[0].get("value") if items else None
        if value is not None and not isinstance(value, Var):
            default = value
        self.register_callback_binding(default)

def RadioItem(label, value=None):
    value = value if value else label
    return {'value': value, 'label': label}


def DropdownItem(
    label: str | Widget,
    value: str | int | float | bool | None = None,
    enabled: bool = True,
) -> dict[str, Any]:
    if not isinstance(label, (str, Widget)):
        raise TypeError("label must be a string or Widget")
    if value is not None and not isinstance(value, (str, int, float, bool)):
        raise TypeError("value must be a string, number, boolean, or None")
    if isinstance(label, Widget) and value is None:
        raise ValueError("value is required when label is a Widget")
    item = {
        "value": label if value is None else value,
    }
    if isinstance(label, Widget):
        item["child"] = label
    else:
        item["label"] = label
    item["enabled"] = enabled
    return item
