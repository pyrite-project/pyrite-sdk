from .base import Widget
from ....interfaces.ui import EventType
from ....interfaces.ui import WidgetType
from typing import Any, Optional

class TextButton(Widget):
    def __init__(
        self,
        on_pressed: Optional[EventType] = None,
        on_long_press: Optional[EventType] = None,
        style: Optional[Any] = None,
        autofocus: Optional[bool] = None,
        **kwargs: Any
    ) -> None:
        super().__init__("TextButton",
                        onPressed = on_pressed,
                        onLongPress = on_long_press,
                        style = style,
                        autofocus = autofocus,
                        **kwargs)

class ElevatedButton(Widget):
    def __init__(
        self,
        on_pressed: Optional[EventType] = None,
        on_long_press: Optional[EventType] = None,
        style: Optional[Any] = None,
        autofocus: Optional[bool] = None,
        **kwargs: Any
    ) -> None:
        super().__init__("ElevatedButton",
                        onPressed = on_pressed,
                        onLongPress = on_long_press,
                        style = style,
                        autofocus = autofocus,
                        **kwargs)

class OutlinedButton(Widget):
    def __init__(
        self,
        on_pressed: Optional[EventType] = None,
        on_long_press: Optional[EventType] = None,
        style: Optional[Any] = None,
        autofocus: Optional[bool] = None,
        **kwargs: Any
    ) -> None:
        super().__init__("OutlinedButton",
                        onPressed = on_pressed,
                        onLongPress = on_long_press,
                        style = style,
                        autofocus = autofocus,
                        **kwargs)

class FilledButton(Widget):
    def __init__(
        self,
        on_pressed: Optional[EventType] = None,
        on_long_press: Optional[EventType] = None,
        on_hover: Optional[EventType] = None,
        on_focus_change: Optional[EventType] = None,
        style: Optional[Any] = None,
        autofocus: Optional[bool] = None,
        clip_behavior: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        super().__init__("FilledButton",
                        onPressed = on_pressed,
                        onLongPress = on_long_press,
                        onHover = on_hover,
                        onFocusChange = on_focus_change,
                        style = style,
                        autofocus = autofocus,
                        clipBehavior = clip_behavior,
                        **kwargs)

class IconButton(Widget):
    def __init__(
        self,
        icon: Any,
        on_pressed: Optional[EventType] = None,
        tooltip: Optional[str] = None,
        icon_size: Optional[Any] = None,
        color: Optional[Any] = None,
        disabled_color: Optional[Any] = None,
        splash_radius: Optional[Any] = None,
        autofocus: Optional[bool] = None,
        **kwargs: Any
    ) -> None:
        if isinstance(icon, WidgetType):
            icon_widget = icon
            if icon_size is not None and icon_widget.args.get("size") is None:
                icon_widget.args["size"] = icon_size
            if color is not None and icon_widget.args.get("color") is None:
                icon_widget.args["color"] = color
        else:
            icon_widget = Widget(
                "Icon",
                icon=icon,
                size=icon_size,
                color=color if on_pressed is not None else disabled_color,
                add_to_parent=False,
            )
        child = Widget(
            "Container",
            width=splash_radius,
            height=splash_radius,
            alignment={"x": 0.0, "y": 0.0},
            child=icon_widget,
            add_to_parent=False,
        )
        super().__init__("GestureDetector",
                        onTap=on_pressed,
                        child=child,
                        **kwargs)

class FloatingActionButton(Widget):
    def __init__(
        self,
        on_pressed: Optional[EventType] = None,
        tooltip: Optional[str] = None,
        foreground_color: Optional[Any] = None,
        background_color: Optional[Any] = None,
        elevation: Optional[Any] = None,
        mini: Optional[bool] = None,
        shape: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        super().__init__("FloatingActionButton",
                        onPressed=on_pressed,
                        tooltip=tooltip,
                        foregroundColor=foreground_color,
                        backgroundColor=background_color,
                        elevation=elevation,
                        mini=mini,
                        shape=shape,
                        **kwargs)
