from .base import Widget
from .media import Icon
from ....interfaces.ui import EventType
from ....interfaces.ui import WidgetType
from typing import Any, Optional


def _icon_widget(icon: Any) -> WidgetType:
    return icon if isinstance(icon, WidgetType) else Icon(
        icon=icon,
        add_to_parent=False,
    )


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
        on_long_press: Optional[EventType] = None,
        on_hover: Optional[EventType] = None,
        selected_icon: Optional[Any] = None,
        is_selected: Optional[bool] = None,
        visual_density: Optional[Any] = None,
        padding: Optional[Any] = None,
        alignment: Optional[Any] = None,
        focus_color: Optional[Any] = None,
        hover_color: Optional[Any] = None,
        highlight_color: Optional[Any] = None,
        splash_color: Optional[Any] = None,
        enable_feedback: Optional[bool] = None,
        constraints: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(
            "IconButton",
            icon=_icon_widget(icon),
            selectedIcon=(
                _icon_widget(selected_icon) if selected_icon is not None else None
            ),
            onPressed=on_pressed,
            onLongPress=on_long_press,
            onHover=on_hover,
            tooltip=tooltip,
            iconSize=icon_size,
            visualDensity=visual_density,
            padding=padding,
            alignment=alignment,
            color=color,
            disabledColor=disabled_color,
            focusColor=focus_color,
            hoverColor=hover_color,
            highlightColor=highlight_color,
            splashColor=splash_color,
            splashRadius=splash_radius,
            autofocus=autofocus,
            enableFeedback=enable_feedback,
            constraints=constraints,
            isSelected=is_selected,
            **kwargs
        )

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
        super().__init__(
            "FloatingActionButton",
            onPressed=on_pressed,
            tooltip=tooltip,
            foregroundColor=foreground_color,
            backgroundColor=background_color,
            elevation=elevation,
            mini=mini,
            shape=shape,
            **kwargs
        )
