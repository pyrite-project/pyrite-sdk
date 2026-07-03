from .base import Widget
from typing import Any, Optional

class Scaffold(Widget):
    def __init__(
        self,
        app_bar: Optional[Any] = None,
        floating_action_button: Optional[Any] = None,
        drawer: Optional[Any] = None,
        end_drawer: Optional[Any] = None,
        background_color: Optional[Any] = None,
        bottom_navigation_bar: Optional[Any] = None,
        resize_to_avoid_bottom_inset: Optional[bool] = None,
        **kwargs: Any
    ) -> None:
        if app_bar is not None:
            kwargs["appBar"] = app_bar
        if floating_action_button is not None:
            kwargs["floatingActionButton"] = floating_action_button
        if end_drawer is not None:
            kwargs["endDrawer"] = end_drawer
        if bottom_navigation_bar is not None:
            kwargs["bottomNavigationBar"] = bottom_navigation_bar
        super().__init__("Scaffold",
                        drawer=drawer,
                        backgroundColor=background_color,
                        resizeToAvoidBottomInset=resize_to_avoid_bottom_inset,
                        **kwargs)
        self._child_keyname = "body"

class AppBar(Widget):
    def __init__(
        self,
        title: Optional[Any] = None,
        leading: Optional[Any] = None,
        actions: Optional[list[Any]] = None,
        background_color: Optional[Any] = None,
        foreground_color: Optional[Any] = None,
        elevation: Optional[Any] = None,
        center_title: Optional[bool] = None,
        **kwargs: Any
    ) -> None:
        super().__init__("AppBar",
                        title=title,
                        leading=leading,
                        actions=actions,
                        backgroundColor=background_color,
                        foregroundColor=foreground_color,
                        elevation=elevation,
                        centerTitle=center_title,
                        **kwargs)
