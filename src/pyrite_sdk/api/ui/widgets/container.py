from .base import Widget
from typing import Any, Optional

class Container(Widget):
    def __init__(
        self,
        color: Optional[Any] = None,
        padding: Optional[Any] = None,
        margin: Optional[Any] = None,
        alignment: Optional[Any] = None,
        width: Optional[Any] = None,
        height: Optional[Any] = None,
        constraints: Optional[Any] = None,
        decoration: Optional[Any] = None,
        foreground_decoration: Optional[Any] = None,
        transform: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        super().__init__("Container",
                        color = color,
                        padding = padding,
                        margin = margin,
                        alignment = alignment,
                        width = width,
                        height = height,
                        constraints = constraints,
                        decoration = decoration,
                        foregroundDecoration = foreground_decoration,
                        transform = transform,
                        **kwargs)

class Center(Widget):
    def __init__(
        self,
        padding: Optional[Any] = None,
        margin: Optional[Any] = None,
        width_factor: Optional[Any] = None,
        height_factor: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        super().__init__("Center",
                        padding=padding,
                        margin=margin,
                        widthFactor=width_factor,
                        heightFactor=height_factor,
                        **kwargs)

class Column(Widget):
    def __init__(
        self,
        padding: Optional[Any] = None,
        margin: Optional[Any] = None,
        main_axis_alignment: Optional[Any] = None,
        cross_axis_alignment: Optional[Any] = None,
        main_axis_size: Optional[Any] = None,
        text_direction: Optional[Any] = None,
        vertical_direction: Optional[Any] = None,
        text_baseline: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        super().__init__("Column",
                        padding=padding,
                        margin=margin,
                        mainAxisAlignment=main_axis_alignment,
                        crossAxisAlignment=cross_axis_alignment,
                        mainAxisSize=main_axis_size,
                        textDirection=text_direction,
                        verticalDirection=vertical_direction,
                        textBaseline=text_baseline,
                        multi_child=True,
                        **kwargs)

class Row(Widget):
    def __init__(
        self,
        padding: Optional[Any] = None,
        margin: Optional[Any] = None,
        main_axis_alignment: Optional[Any] = None,
        cross_axis_alignment: Optional[Any] = None,
        main_axis_size: Optional[Any] = None,
        text_direction: Optional[Any] = None,
        vertical_direction: Optional[Any] = None,
        text_baseline: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        super().__init__("Row",
                        padding=padding,
                        margin=margin,
                        mainAxisAlignment=main_axis_alignment,
                        crossAxisAlignment=cross_axis_alignment,
                        mainAxisSize=main_axis_size,
                        textDirection=text_direction,
                        verticalDirection=vertical_direction,
                        textBaseline=text_baseline,
                        multi_child=True,
                        **kwargs)

class Expanded(Widget):
    def __init__(self, flex: Optional[int] = None, **kwargs: Any) -> None:
        super().__init__("Expanded",
                        flex=flex,
                        **kwargs)

class Flexible(Widget):
    def __init__(
        self,
        flex: Optional[int] = None,
        fit: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        super().__init__("Flexible",
                        flex=flex,
                        fit=fit,
                        **kwargs)

class Spacer(Widget):
    def __init__(self, flex: Optional[int] = None, **kwargs: Any) -> None:
        super().__init__("Spacer",
                        flex=flex,
                        **kwargs)

class FittedBox(Widget):
    def __init__(
        self,
        fit: Optional[Any] = None,
        alignment: Optional[Any] = None,
        clip_behavior: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        super().__init__("FittedBox",
                        fit=fit,
                        alignment=alignment,
                        clipBehavior=clip_behavior,
                        **kwargs)

class Padding(Widget):
    def __init__(self, padding: Any, **kwargs: Any) -> None:
        super().__init__("Padding",
                        padding=padding,
                        **kwargs)

class SizedBox(Widget):
    def __init__(
        self,
        width: Optional[Any] = None,
        height: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        super().__init__("SizedBox",
                        width=width,
                        height=height,
                        **kwargs)

class Align(Widget):
    def __init__(
        self,
        alignment: Optional[Any] = None,
        width_factor: Optional[Any] = None,
        height_factor: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        super().__init__("Align",
                        alignment=alignment,
                        widthFactor=width_factor,
                        heightFactor=height_factor,
                        **kwargs)

class Stack(Widget):
    def __init__(
        self,
        alignment: Optional[Any] = None,
        text_direction: Optional[Any] = None,
        fit: Optional[Any] = None,
        clip_behavior: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        super().__init__("Stack",
                        alignment=alignment,
                        textDirection=text_direction,
                        fit=fit,
                        clipBehavior=clip_behavior,
                        multi_child=True,
                        **kwargs)

class Positioned(Widget):
    def __init__(
        self,
        left: Optional[Any] = None,
        top: Optional[Any] = None,
        right: Optional[Any] = None,
        bottom: Optional[Any] = None,
        width: Optional[Any] = None,
        height: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        super().__init__("Positioned",
                        left=left,
                        top=top,
                        right=right,
                        bottom=bottom,
                        width=width,
                        height=height,
                        **kwargs)

class SafeArea(Widget):
    def __init__(
        self,
        left: Optional[bool] = None,
        top: Optional[bool] = None,
        right: Optional[bool] = None,
        bottom: Optional[bool] = None,
        minimum: Optional[Any] = None,
        maintain_bottom_view_padding: Optional[bool] = None,
        **kwargs: Any
    ) -> None:
        super().__init__("SafeArea",
                        left=left,
                        top=top,
                        right=right,
                        bottom=bottom,
                        minimum=minimum,
                        maintainBottomViewPadding=maintain_bottom_view_padding,
                        **kwargs)

class SingleChildScrollView(Widget):
    def __init__(
        self,
        scroll_direction: Optional[Any] = None,
        reverse: Optional[bool] = None,
        padding: Optional[Any] = None,
        primary: Optional[bool] = None,
        **kwargs: Any
    ) -> None:
        super().__init__("SingleChildScrollView",
                        scrollDirection=scroll_direction,
                        reverse=reverse,
                        padding=padding,
                        primary=primary,
                        **kwargs)

class ListView(Widget):
    def __init__(
        self,
        scroll_direction: Optional[Any] = None,
        reverse: Optional[bool] = None,
        padding: Optional[Any] = None,
        primary: Optional[bool] = None,
        shrink_wrap: Optional[bool] = None,
        **kwargs: Any
    ) -> None:
        super().__init__("ListView",
                        scrollDirection=scroll_direction,
                        reverse=reverse,
                        padding=padding,
                        primary=primary,
                        shrinkWrap=shrink_wrap,
                        multi_child=True,
                        **kwargs)

class Wrap(Widget):
    def __init__(
        self,
        direction: Optional[Any] = None,
        alignment: Optional[Any] = None,
        spacing: Optional[Any] = None,
        run_alignment: Optional[Any] = None,
        run_spacing: Optional[Any] = None,
        cross_axis_alignment: Optional[Any] = None,
        text_direction: Optional[Any] = None,
        vertical_direction: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        super().__init__("Wrap",
                        direction=direction,
                        alignment=alignment,
                        spacing=spacing,
                        runAlignment=run_alignment,
                        runSpacing=run_spacing,
                        crossAxisAlignment=cross_axis_alignment,
                        textDirection=text_direction,
                        verticalDirection=vertical_direction,
                        multi_child=True,
                        **kwargs)

class Divider(Widget):
    def __init__(
        self,
        height: Optional[Any] = None,
        thickness: Optional[Any] = None,
        indent: Optional[Any] = None,
        end_indent: Optional[Any] = None,
        color: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        super().__init__("Divider",
                        height=height,
                        thickness=thickness,
                        indent=indent,
                        endIndent=end_indent,
                        color=color,
                        **kwargs)

class Card(Widget):
    def __init__(
        self,
        color: Optional[Any] = None,
        elevation: Optional[Any] = None,
        margin: Optional[Any] = None,
        shape: Optional[Any] = None,
        clip_behavior: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        super().__init__("Card",
                        color=color,
                        elevation=elevation,
                        margin=margin,
                        shape=shape,
                        clipBehavior=clip_behavior,
                        **kwargs)
