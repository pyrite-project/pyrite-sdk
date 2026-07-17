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
        source: Any,
        source_type: Optional[Any] = "file",
        width: Optional[Any] = None,
        height: Optional[Any] = None,
        scale: Optional[Any] = None,
        package: Optional[str] = None,
        color: Optional[Any] = None,
        color_blend_mode: Optional[Any] = None,
        fit: Optional[Any] = None,
        alignment: Optional[Any] = None,
        repeat: Optional[Any] = None,
        semantic_label: Optional[str] = None,
        exclude_from_semantics: Optional[bool] = None,
        filter_quality: Optional[Any] = None,
        gapless_playback: Optional[bool] = None,
        is_anti_alias: Optional[bool] = None,
        cache_width: Optional[int] = None,
        cache_height: Optional[int] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(
            "Image",
            source=source,
            sourceType=source_type,
            width=width,
            height=height,
            scale=scale,
            package=package,
            color=color,
            colorBlendMode=color_blend_mode,
            fit=fit,
            alignment=alignment,
            repeat=repeat,
            semanticLabel=semantic_label,
            excludeFromSemantics=exclude_from_semantics,
            filterQuality=filter_quality,
            gaplessPlayback=gapless_playback,
            isAntiAlias=is_anti_alias,
            cacheWidth=cache_width,
            cacheHeight=cache_height,
            **kwargs
        )


class VideoPlayer(Widget):
    def __init__(
        self,
        source: Any,
        source_type: Optional[Any] = "file",
        width: Optional[Any] = None,
        height: Optional[Any] = None,
        package: Optional[str] = None,
        autoplay: Optional[bool] = False,
        looping: Optional[bool] = False,
        muted: Optional[bool] = False,
        show_controls: Optional[bool] = True,
        fit: Optional[Any] = "contain",
        **kwargs: Any
    ) -> None:
        super().__init__(
            "VideoPlayer",
            source=source,
            sourceType=source_type,
            width=width,
            height=height,
            package=package,
            autoplay=autoplay,
            looping=looping,
            muted=muted,
            showControls=show_controls,
            fit=fit,
            **kwargs
        )


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
        super().__init__(
            "ListTile",
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
            **kwargs
        )


class Tooltip(Widget):
    def __init__(
        self,
        message: Any,
        constraints: Optional[Any] = None,
        padding: Optional[Any] = None,
        margin: Optional[Any] = None,
        vertical_offset: Optional[Any] = None,
        prefer_below: Optional[bool] = None,
        exclude_from_semantics: Optional[bool] = None,
        text_style: Optional[Any] = None,
        text_align: Optional[Any] = None,
        wait_duration: Optional[Any] = None,
        show_duration: Optional[Any] = None,
        exit_duration: Optional[Any] = None,
        enable_tap_to_dismiss: Optional[bool] = None,
        trigger_mode: Optional[Any] = None,
        enable_feedback: Optional[bool] = None,
        on_triggered: Optional[EventType] = None,
        ignore_pointer: Optional[bool] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(
            "Tooltip",
            message=message,
            constraints=constraints,
            padding=padding,
            margin=margin,
            verticalOffset=vertical_offset,
            preferBelow=prefer_below,
            excludeFromSemantics=exclude_from_semantics,
            textStyle=text_style,
            textAlign=text_align,
            waitDuration=wait_duration,
            showDuration=show_duration,
            exitDuration=exit_duration,
            enableTapToDismiss=enable_tap_to_dismiss,
            triggerMode=trigger_mode,
            enableFeedback=enable_feedback,
            onTriggered=on_triggered,
            ignorePointer=ignore_pointer,
            **kwargs
        )


class Chip(Widget):
    def __init__(
        self,
        label: Any,
        avatar: Optional[Any] = None,
        delete_icon: Optional[Any] = None,
        on_deleted: Optional[EventType] = None,
        label_style: Optional[Any] = None,
        label_padding: Optional[Any] = None,
        background_color: Optional[Any] = None,
        padding: Optional[Any] = None,
        delete_icon_color: Optional[Any] = None,
        tooltip: Optional[str] = None,
        delete_button_tooltip_message: Optional[str] = None,
        side: Optional[Any] = None,
        shape: Optional[Any] = None,
        clip_behavior: Optional[Any] = None,
        visual_density: Optional[Any] = None,
        material_tap_target_size: Optional[Any] = None,
        elevation: Optional[Any] = None,
        shadow_color: Optional[Any] = None,
        surface_tint_color: Optional[Any] = None,
        icon_theme: Optional[Any] = None,
        autofocus: Optional[bool] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(
            "Chip",
            label=label,
            avatar=avatar,
            deleteIcon=delete_icon,
            onDeleted=on_deleted,
            labelStyle=label_style,
            labelPadding=label_padding,
            backgroundColor=background_color,
            padding=padding,
            deleteIconColor=delete_icon_color,
            tooltip=tooltip,
            deleteButtonTooltipMessage=delete_button_tooltip_message,
            side=side,
            shape=shape,
            clipBehavior=clip_behavior,
            visualDensity=visual_density,
            materialTapTargetSize=material_tap_target_size,
            elevation=elevation,
            shadowColor=shadow_color,
            surfaceTintColor=surface_tint_color,
            iconTheme=icon_theme,
            autofocus=autofocus,
            **kwargs
        )


class ExpansionTile(Widget):
    def __init__(
        self,
        title: Any,
        leading: Optional[Any] = None,
        subtitle: Optional[Any] = None,
        trailing: Optional[Any] = None,
        show_trailing_icon: Optional[bool] = None,
        on_expansion_changed: Optional[EventType] = None,
        initially_expanded: Optional[bool] = None,
        maintain_state: Optional[bool] = None,
        tile_padding: Optional[Any] = None,
        expanded_cross_axis_alignment: Optional[Any] = None,
        expanded_alignment: Optional[Any] = None,
        children_padding: Optional[Any] = None,
        background_color: Optional[Any] = None,
        collapsed_background_color: Optional[Any] = None,
        text_color: Optional[Any] = None,
        collapsed_text_color: Optional[Any] = None,
        icon_color: Optional[Any] = None,
        collapsed_icon_color: Optional[Any] = None,
        shape: Optional[Any] = None,
        collapsed_shape: Optional[Any] = None,
        clip_behavior: Optional[Any] = None,
        control_affinity: Optional[Any] = None,
        dense: Optional[bool] = None,
        visual_density: Optional[Any] = None,
        min_tile_height: Optional[Any] = None,
        enable_feedback: Optional[bool] = None,
        enabled: Optional[bool] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(
            "ExpansionTile",
            title=title,
            leading=leading,
            subtitle=subtitle,
            trailing=trailing,
            showTrailingIcon=show_trailing_icon,
            onExpansionChanged=on_expansion_changed,
            initiallyExpanded=initially_expanded,
            maintainState=maintain_state,
            tilePadding=tile_padding,
            expandedCrossAxisAlignment=expanded_cross_axis_alignment,
            expandedAlignment=expanded_alignment,
            childrenPadding=children_padding,
            backgroundColor=background_color,
            collapsedBackgroundColor=collapsed_background_color,
            textColor=text_color,
            collapsedTextColor=collapsed_text_color,
            iconColor=icon_color,
            collapsedIconColor=collapsed_icon_color,
            shape=shape,
            collapsedShape=collapsed_shape,
            clipBehavior=clip_behavior,
            controlAffinity=control_affinity,
            dense=dense,
            visualDensity=visual_density,
            minTileHeight=min_tile_height,
            enableFeedback=enable_feedback,
            enabled=enabled,
            multi_child=True,
            **kwargs
        )


class CircularProgressIndicator(Widget):
    def __init__(
        self,
        value: Optional[Any] = None,
        background_color: Optional[Any] = None,
        color: Optional[Any] = None,
        stroke_width: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(
            "CircularProgressIndicator",
            value=value,
            backgroundColor=background_color,
            color=color,
            strokeWidth=stroke_width,
            **kwargs
        )


class LinearProgressIndicator(Widget):
    def __init__(
        self,
        value: Optional[Any] = None,
        background_color: Optional[Any] = None,
        color: Optional[Any] = None,
        min_height: Optional[Any] = None,
        **kwargs: Any
    ) -> None:
        super().__init__(
            "LinearProgressIndicator",
            value=value,
            backgroundColor=background_color,
            color=color,
            minHeight=min_height,
            **kwargs
        )
