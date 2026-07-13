from .base import Widget
from ....interfaces.ui import EventType
from ..sentence import RFWData
from typing import Any, Optional


def _icon_args(icon: Any) -> dict[str, Any]:
    """Return the flattened RFW arguments expected by the host Icon builder."""
    value = icon.value if isinstance(icon, RFWData) else icon
    if isinstance(value, dict) and "icon" in value:
        return dict(value)
    return {"icon": icon}


class Icon(Widget):
    def __init__(
        self,
        icon: Any,
        size: Optional[Any] = None,
        color: Optional[Any] = None,
        semantic_label: Optional[str] = None,
        text_direction: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        icon_args = _icon_args(icon)
        icon_args.update(
            size=size,
            color=color,
            semanticLabel=semantic_label,
            textDirection=text_direction,
        )
        icon_args.update(kwargs)
        super().__init__("Icon", **icon_args)


class Image(Widget):
    def __init__(
        self,
        image: Any,
        width: Optional[Any] = None,
        height: Optional[Any] = None,
        color: Optional[Any] = None,
        fit: Optional[Any] = None,
        alignment: Optional[Any] = None,
        repeat: Optional[Any] = None,
        semantic_label: Optional[str] = None,
        **kwargs: Any
    ) -> None:
        super().__init__("Image",
                        image=image,
                        width=width,
                        height=height,
                        color=color,
                        fit=fit,
                        alignment=alignment,
                        repeat=repeat,
                        semanticLabel=semantic_label,
                        **kwargs)


class ListTile(Widget):
    def __init__(
        self,
        leading: Optional[Any] = None,
        title: Optional[Any] = None,
        subtitle: Optional[Any] = None,
        trailing: Optional[Any] = None,
        is_three_line: Optional[bool] = None,
        dense: Optional[bool] = None,
        enabled: Optional[bool] = None,
        selected: Optional[bool] = None,
        on_tap: Optional[EventType] = None,
        on_long_press: Optional[EventType] = None,
        content_padding: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        super().__init__("ListTile",
                        leading=leading,
                        title=title,
                        subtitle=subtitle,
                        trailing=trailing,
                        isThreeLine=is_three_line,
                        dense=dense,
                        enabled=enabled,
                        selected=selected,
                        onTap=on_tap,
                        onLongPress=on_long_press,
                        contentPadding=content_padding,
                        **kwargs)


class CircularProgressIndicator(Widget):
    def __init__(
        self,
        value: Optional[Any] = None,
        background_color: Optional[Any] = None,
        color: Optional[Any] = None,
        stroke_width: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        super().__init__("CircularProgressIndicator",
                        value=value,
                        backgroundColor=background_color,
                        color=color,
                        strokeWidth=stroke_width,
                        **kwargs)


class LinearProgressIndicator(Widget):
    def __init__(
        self,
        value: Optional[Any] = None,
        background_color: Optional[Any] = None,
        color: Optional[Any] = None,
        min_height: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        super().__init__("LinearProgressIndicator",
                        value=value,
                        backgroundColor=background_color,
                        color=color,
                        minHeight=min_height,
                        **kwargs)
