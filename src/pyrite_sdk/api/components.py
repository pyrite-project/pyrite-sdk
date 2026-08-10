"""Builders for the native common component layer.

Each helper returns a plain schema node (``{"type", "props", "children",
"events"}``) that the IDE validates against its component registry. The shapes
here must match that registry exactly; the shared fixture cross-checks both
sides.

Native components are declarative data, not executable widget code, and their
events are delivered as ``ide.view.event`` frames.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Iterable, Literal, Optional

from .icons import MaterialIcon
from .resources import PluginResource


def _icon(value: Optional[MaterialIcon]) -> Optional[str]:
    if value is not None and not isinstance(value, MaterialIcon):
        raise TypeError("icon values must use pyrite_sdk.api.icons.Icons")
    return str(value) if value is not None else None


#: Schema version this builder set targets. Must match the host's
#: ``componentSchemaVersion``.
COMPONENT_SCHEMA_VERSION: int = 1


class Component(dict[str, Any]):
    """A component schema node.

    Subclasses ``dict`` so it serializes directly into a view snapshot/patch,
    while still offering a small API for attaching handlers.
    """

    def __init__(
        self,
        type: str,
        props: Optional[dict[str, Any]] = None,
        children: Optional[list[Any]] = None,
        events: Optional[dict[str, Callable[..., Any]]] = None,
    ) -> None:
        super().__init__()
        self["type"] = type
        if props:
            # Drop None values so optional props are simply absent.
            cleaned = {k: v for k, v in props.items() if v is not None}
            if cleaned:
                self["props"] = cleaned
        if children:
            self["children"] = children
        if events:
            self["events"] = events
        self._view_model: Any = None
        self._controller: Optional[ComponentController] = None

    @property
    def id(self) -> Optional[str]:
        return self.get("props", {}).get("id")

    def on(self, event: str, handler: Callable[..., Any]) -> "Component":
        """Attaches [handler] for [event]; returns self for chaining.

        The handler is stored on the node and collected by
        :func:`collect_handlers` when the tree is sent.
        """
        self.setdefault("events", {})[event] = handler
        return self

    @property
    def controller(self) -> ComponentController:
        """Imperative controller for this mounted component."""
        if self._controller is None:
            controller_type = _CONTROLLERS.get(
                str(self.get("type", "")), ComponentController
            )
            self._controller = controller_type(self)
        return self._controller

    def _bind_view(self, view_model: Any) -> None:
        self._view_model = view_model
        for child in self.get("children", ()):
            _bind_component_value(child, view_model)

    def _invoke(
        self,
        method: str,
        arguments: Optional[dict[str, Any]] = None,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        if self._view_model is None:
            raise RuntimeError("component is not bound to a ViewModel")
        if not self.id:
            raise ValueError("component requires an id before using its controller")
        self._view_model.invoke_component(
            self.id, method, arguments or {}, callback=callback
        )

    def to_json(self) -> dict[str, Any]:
        """Returns the node with handlers replaced by their event names.

        The wire form carries only ``{event: True}`` markers; the host echoes the
        event name back and the SDK looks the handler up locally.
        """
        node: dict[str, Any] = {"type": self["type"]}
        if "props" in self:
            node["props"] = self["props"]
        if "events" in self:
            node["events"] = {name: True for name in self["events"]}
        if "children" in self:
            node["children"] = [
                _wire_component_value(child) for child in self["children"]
            ]
        return node


def _bind_component_value(value: Any, view_model: Any) -> None:
    if isinstance(value, Component):
        value._bind_view(view_model)
    elif isinstance(value, dict):
        for child in value.values():
            _bind_component_value(child, view_model)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _bind_component_value(child, view_model)


def _wire_component_value(value: Any) -> Any:
    if isinstance(value, Component):
        return value.to_json()
    if isinstance(value, dict):
        return {key: _wire_component_value(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_wire_component_value(child) for child in value]
    return value


class ComponentController:
    def __init__(self, component: Component) -> None:
        self.component: Component = component

    def _call(
        self,
        method: str,
        callback: Optional[Callable[..., Any]] = None,
        **arguments: Any,
    ) -> None:
        self.component._invoke(method, arguments, callback)

    def is_mounted(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("is_mounted", callback)

    def ensure_visible(
        self,
        alignment: int | float = 0.5,
        animated: bool = True,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._call("ensure_visible", callback, alignment=alignment, animated=animated)

    def get_bounds(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("get_bounds", callback)

    def request_focus(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("request_focus", callback)

    def unfocus(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("unfocus", callback)


class TextFieldController(ComponentController):
    def get_text(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("get_text", callback)

    def set_text(
        self, text: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("set_text", callback, text=text)

    def clear(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("clear", callback)

    def select_all(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("select_all", callback)

    def get_selection(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("get_selection", callback)

    def set_selection(
        self,
        start: int,
        end: Optional[int] = None,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._call(
            "set_selection", callback, start=start, end=start if end is None else end
        )

    def replace_selection(
        self, text: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("replace_selection", callback, text=text)


class NumberFieldController(TextFieldController):
    def get_value(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("get_value", callback)

    def set_value(
        self,
        value: int | float,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._call("set_value", callback, value=value)

    def increment(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("increment", callback)

    def decrement(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("decrement", callback)


class VirtualListController(ComponentController):
    def select(
        self, id: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("select", callback, id=id)

    def clear_selection(
        self, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("clear_selection", callback)

    def reveal_item(
        self,
        id: str,
        animated: bool = True,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._call("reveal_item", callback, id=id, animated=animated)

    def jump_to_index(
        self, index: int, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("jump_to_index", callback, index=index)

    def animate_to_index(
        self, index: int, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("animate_to_index", callback, index=index)

    def scroll_by(
        self,
        delta: int | float,
        animated: bool = True,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._call("scroll_by", callback, delta=delta, animated=animated)

    def get_visible_range(
        self, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("get_visible_range", callback)


class TreeViewController(ComponentController):
    def select(
        self, id: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("select", callback, id=id)

    def clear_selection(
        self, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("clear_selection", callback)

    def reveal(
        self,
        id: str,
        animated: bool = True,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._call("reveal", callback, id=id, animated=animated)

    def expand(
        self, id: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("expand", callback, id=id)

    def collapse(
        self, id: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("collapse", callback, id=id)

    def toggle(
        self, id: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("toggle", callback, id=id)

    def expand_all(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("expand_all", callback)

    def collapse_all(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("collapse_all", callback)

    def is_expanded(
        self, id: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("is_expanded", callback, id=id)

    def get_visible_nodes(
        self, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("get_visible_nodes", callback)


class PropertyGridController(TreeViewController):
    def activate(
        self, id: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("activate", callback, id=id)


class DataTableController(ComponentController):
    def select_row(
        self, id: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("select_row", callback, id=id)

    def clear_selection(
        self, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("clear_selection", callback)

    def reveal_row(
        self,
        id: str,
        animated: bool = True,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._call("reveal_row", callback, id=id, animated=animated)

    def reveal_cell(
        self,
        row_id: str,
        column_id: str,
        animated: bool = True,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._call(
            "reveal_cell", callback, rowId=row_id, columnId=column_id, animated=animated
        )

    def jump_to_row(
        self, index: int, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("jump_to_row", callback, index=index)

    def animate_to_row(
        self, index: int, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("animate_to_row", callback, index=index)

    def get_visible_range(
        self, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("get_visible_range", callback)


class TabsController(ComponentController):
    def select(
        self, id: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("select", callback, id=id)

    def next(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("next", callback)

    def previous(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("previous", callback)

    def get_selected(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("get_selected", callback)


class SectionController(ComponentController):
    def expand(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("expand", callback)

    def collapse(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("collapse", callback)

    def toggle(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("toggle", callback)

    def is_expanded(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("is_expanded", callback)


class SplitViewController(ComponentController):
    def get_ratios(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("get_ratios", callback)

    def set_ratio(
        self,
        index: int,
        ratio: int | float,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._call("set_ratio", callback, index=index, ratio=ratio)

    def set_ratios(
        self,
        ratios: Iterable[int | float],
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._call("set_ratios", callback, ratios=list(ratios))

    def reset(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("reset", callback)


class VideoController(ComponentController):
    def play(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("play", callback)

    def pause(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("pause", callback)

    def seek_to(
        self, position_ms: int, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("seek_to", callback, positionMs=position_ms)

    def set_volume(
        self,
        volume: int | float,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._call("set_volume", callback, volume=volume)

    def set_speed(
        self,
        speed: int | float,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._call("set_speed", callback, speed=speed)

    def set_looping(
        self, looping: bool, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("set_looping", callback, looping=looping)

    def get_state(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("get_state", callback)

    def enter_fullscreen(
        self, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("enter_fullscreen", callback)

    def exit_fullscreen(
        self, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("exit_fullscreen", callback)


class ImageController(ComponentController):
    def reload(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("reload", callback)

    def evict_cache(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("evict_cache", callback)

    def get_intrinsic_size(
        self, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("get_intrinsic_size", callback)


class MarkdownController(ComponentController):
    def scroll_to_anchor(
        self, anchor: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("scroll_to_anchor", callback, anchor=anchor)

    def get_anchor_offset(
        self, anchor: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("get_anchor_offset", callback, anchor=anchor)

    def select_all(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("select_all", callback)

    def copy_selection(
        self, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("copy_selection", callback)


class MenuController(ComponentController):
    def open(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("open", callback)

    def close(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("close", callback)

    def toggle(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("toggle", callback)

    def is_open(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("is_open", callback)


class MenuBarController(ComponentController):
    def open_menu(
        self, id: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("open_menu", callback, id=id)

    def close(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("close", callback)

    def is_open(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("is_open", callback)


class DropdownController(ComponentController):
    def open(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("open", callback)

    def close(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("close", callback)

    def select(
        self, id: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("select", callback, id=id)

    def get_selected(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("get_selected", callback)

    def is_open(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("is_open", callback)


class ContextMenuController(ComponentController):
    def show(
        self,
        x: Optional[int | float] = None,
        y: Optional[int | float] = None,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._call("show", callback, x=x, y=y)

    def close(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("close", callback)

    def is_open(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("is_open", callback)


class DialogController(ComponentController):
    def show(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("show", callback)

    def close(
        self,
        result: Any = None,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._call("close", callback, result=result)

    def is_open(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("is_open", callback)


class CanvasController(ComponentController):
    """Imperative control of a mounted Canvas surface.

    ``push_ops``/``set_ops`` write to the *ephemeral* overlay layer (lost on
    resync/visibility-restore); persistent primitives belong in ``props.ops``.
    Unlike snapshot/patch, invoke does not pass through the view payload guard,
    so both enforce the 2 MiB arguments cap here, mirroring ``ViewModel``.
    """

    #: Mirror of view.MAX_VIEW_PAYLOAD_BYTES (imported lazily to avoid a cycle).
    MAX_VIEW_PAYLOAD_BYTES: int = 2 * 1024 * 1024

    def _guard_ops(self, arguments: dict[str, Any]) -> None:
        import json

        from .view import ViewProtocolError

        size = len(json.dumps(arguments, separators=(",", ":")).encode("utf-8"))
        if size > self.MAX_VIEW_PAYLOAD_BYTES:
            raise ViewProtocolError(
                f"canvas ops exceed {self.MAX_VIEW_PAYLOAD_BYTES} bytes"
            )

    def push_ops(
        self,
        ops: Iterable[dict[str, Any]],
        layer: Optional[str] = None,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        arguments: dict[str, Any] = {"ops": list(ops)}
        if layer is not None:
            arguments["layer"] = layer
        self._guard_ops(arguments)
        self.component._invoke("push_ops", arguments, callback)

    def set_ops(
        self,
        ops: Iterable[dict[str, Any]],
        layer: Optional[str] = None,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        arguments: dict[str, Any] = {"ops": list(ops)}
        if layer is not None:
            arguments["layer"] = layer
        self._guard_ops(arguments)
        self.component._invoke("set_ops", arguments, callback)

    def clear(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._call("clear", callback)

    def clear_layer(
        self, layer: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._call("clear_layer", callback, layer=layer)

    def hit_test(
        self,
        x: int | float,
        y: int | float,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._call("hit_test", callback, x=x, y=y)


_CONTROLLERS: dict[str, type[ComponentController]] = {
    "TextField": TextFieldController,
    "NumberField": NumberFieldController,
    "VirtualList": VirtualListController,
    "TreeView": TreeViewController,
    "PropertyGrid": PropertyGridController,
    "DataTable": DataTableController,
    "Tabs": TabsController,
    "Section": SectionController,
    "SplitView": SplitViewController,
    "Video": VideoController,
    "Image": ImageController,
    "Markdown": MarkdownController,
    "Menu": MenuController,
    "MenuBar": MenuBarController,
    "Dropdown": DropdownController,
    "ContextMenu": ContextMenuController,
    "Dialog": DialogController,
    "Canvas": CanvasController,
}


class DataItem(dict[str, Any]):
    """Base for typed rows that still serialize as ordinary wire maps."""

    @property
    def id(self) -> str:
        return str(self["id"])

    @property
    def metadata(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in self.items()
            if key
            not in {
                "id",
                "label",
                "icon",
                "parentId",
                "hasChildren",
                "cells",
            }
        }


class ListItem(DataItem):
    def __init__(
        self,
        *,
        id: str,
        label: str,
        icon: Optional[MaterialIcon] = None,
        **data: Any,
    ) -> None:
        super().__init__(id=id, label=label, **data)
        if icon is not None:
            self["icon"] = _icon(icon)

    @property
    def label(self) -> str:
        return str(self["label"])

    @property
    def icon(self) -> Optional[str]:
        value = self.get("icon")
        return str(value) if value is not None else None


class TreeNode(ListItem):
    def __init__(
        self,
        *,
        id: str,
        label: str,
        parent_id: Optional[str] = None,
        icon: Optional[MaterialIcon] = None,
        has_children: bool = False,
        **data: Any,
    ) -> None:
        super().__init__(
            id=id,
            label=label,
            icon=icon,
            parentId=parent_id,
            hasChildren=has_children,
            **data,
        )

    @property
    def parent_id(self) -> Optional[str]:
        value = self.get("parentId")
        return str(value) if value is not None else None

    @property
    def has_children(self) -> bool:
        return bool(self.get("hasChildren", False))


class TableRow(DataItem):
    def __init__(
        self, *, id: str, cells: dict[str, Any], **data: Any
    ) -> None:
        super().__init__(id=id, cells=cells, **data)

    @property
    def cells(self) -> dict[str, Any]:
        return self["cells"]


class TableColumn(dict[str, Any]):
    def __init__(
        self,
        *,
        id: str,
        label: str,
        width: Optional[int | float] = None,
        flex: Optional[int | float] = None,
        frozen: Optional[bool] = None,
        sortable: Optional[bool] = None,
    ) -> None:
        super().__init__(id=id, label=label)
        for key, value in (
            ("width", width),
            ("flex", flex),
            ("frozen", frozen),
            ("sortable", sortable),
        ):
            if value is not None:
                self[key] = value

    @property
    def id(self) -> str:
        return str(self["id"])

    @property
    def label(self) -> str:
        return str(self["label"])


class PropertyEntry(DataItem):
    def __init__(
        self,
        *,
        id: str,
        name: str,
        value: Any = "",
        type_name: str = "",
        parent_id: Optional[str] = None,
        has_children: bool = False,
        **metadata: Any,
    ) -> None:
        super().__init__(
            id=id,
            name=name,
            value=value,
            type=type_name,
            parentId=parent_id,
            hasChildren=has_children,
            **metadata,
        )

    @property
    def name(self) -> str:
        return str(self.get("name", ""))

    @property
    def value(self) -> Any:
        return self.get("value")

    @property
    def type_name(self) -> str:
        return str(self.get("type", ""))

    @property
    def parent_id(self) -> Optional[str]:
        value = self.get("parentId")
        return str(value) if value is not None else None


class SelectOption(dict[str, Any]):
    def __init__(
        self, *, value: str, label: str, disabled: bool = False
    ) -> None:
        super().__init__(value=value, label=label, disabled=disabled)

    @property
    def value(self) -> str:
        return str(self["value"])

    @property
    def label(self) -> str:
        return str(self["label"])


class RangeRequest(dict[str, Any]):
    def __init__(self, payload: dict[str, Any]) -> None:
        super().__init__(payload)

    @property
    def start(self) -> int:
        return int(self.get("start", 0))

    @property
    def count(self) -> int:
        return int(self.get("count", 0))


def collect_handlers(
    node: Any,
    into: Optional[dict[tuple[str, str], Callable[..., Any]]] = None,
) -> dict[tuple[str, str], Callable[..., Any]]:
    """Walks a component tree collecting ``(component_id, event) -> handler``."""
    handlers: dict[tuple[str, str], Callable[..., Any]] = {} if into is None else into
    if isinstance(node, Component):
        component_id = node.id
        if component_id:
            for event, handler in node.get("events", {}).items():
                if callable(handler):
                    handlers[(component_id, event)] = handler
        for child in node.get("children", []) or []:
            collect_handlers(child, handlers)
    elif isinstance(node, (list, tuple)):
        for item in node:
            collect_handlers(item, handlers)
    elif isinstance(node, dict):
        for item in node.values():
            collect_handlers(item, handlers)
    return handlers


# -- Layout -------------------------------------------------------------------


def Row(
    *children: Component,
    id: Optional[str] = None,
    gap: Optional[int | float] = None,
    align: Optional[Literal["start", "center", "end", "stretch"]] = None,
    justify: Optional[
        Literal["start", "center", "end", "spaceBetween", "spaceAround"]
    ] = None,
) -> Component:
    return Component(
        "Row",
        {"id": id, "gap": gap, "align": align, "justify": justify},
        list(children),
    )


def Column(
    *children: Component,
    id: Optional[str] = None,
    gap: Optional[int | float] = None,
    align: Optional[Literal["start", "center", "end", "stretch"]] = None,
    justify: Optional[
        Literal["start", "center", "end", "spaceBetween", "spaceAround"]
    ] = None,
) -> Component:
    return Component(
        "Column",
        {"id": id, "gap": gap, "align": align, "justify": justify},
        list(children),
    )


def Flex(
    *children: Component,
    id: Optional[str] = None,
    direction: Optional[Literal["horizontal", "vertical"]] = None,
    flex: Optional[int | float] = None,
    gap: Optional[int | float] = None,
) -> Component:
    return Component(
        "Flex",
        {"id": id, "direction": direction, "flex": flex, "gap": gap},
        list(children),
    )


def Grid(
    *children: Component,
    columns: int | float,
    id: Optional[str] = None,
    gap: Optional[int | float] = None,
) -> Component:
    return Component("Grid", {"id": id, "columns": columns, "gap": gap}, list(children))


def Wrap(
    *children: Component,
    id: Optional[str] = None,
    gap: Optional[int | float] = None,
    run_gap: Optional[int | float] = None,
) -> Component:
    return Component("Wrap", {"id": id, "gap": gap, "runGap": run_gap}, list(children))


def SplitView(
    *children: Component,
    id: Optional[str] = None,
    direction: Optional[Literal["horizontal", "vertical"]] = None,
    initial_ratio: Optional[int | float] = None,
) -> Component:
    return Component(
        "SplitView",
        {"id": id, "direction": direction, "initialRatio": initial_ratio},
        list(children),
    )


def Tabs(
    *children: Component,
    id: Optional[str] = None,
    selected: Optional[str] = None,
) -> Component:
    return Component("Tabs", {"id": id, "selected": selected}, list(children))


def Tab(
    child: Optional[Component] = None,
    *,
    id: str,
    label: str,
    icon: Optional[MaterialIcon] = None,
) -> Component:
    return Component(
        "Tab",
        {"id": id, "label": label, "icon": _icon(icon)},
        [child] if child is not None else None,
    )


def Section(
    *children: Component,
    id: Optional[str] = None,
    title: Optional[str] = None,
    collapsible: Optional[bool] = None,
    collapsed: Optional[bool] = None,
) -> Component:
    return Component(
        "Section",
        {"id": id, "title": title, "collapsible": collapsible, "collapsed": collapsed},
        list(children),
    )


def Toolbar(
    *children: Component,
    id: Optional[str] = None,
    dense: Optional[bool] = None,
) -> Component:
    return Component("Toolbar", {"id": id, "dense": dense}, list(children))


def AppBar(
    *actions: Component,
    id: Optional[str] = None,
    title: Optional[str] = None,
) -> Component:
    """A title bar with action children.

    Actions are ``IconButton``/``Menu``/``Dropdown`` components passed
    positionally; each carries its own handler. The component-tree ``AppBar``
    renders only these action children and never the manifest command menu.
    """
    return Component("AppBar", {"id": id, "title": title}, list(actions))


def Scaffold(
    *body: Component,
    id: Optional[str] = None,
    app_bar: Optional[Component] = None,
) -> Component:
    """A two-slot page skeleton: an optional top ``AppBar`` and a body.

    ``app_bar`` is placed as ``children[0]`` so the wire order matches the
    host's "first child of type AppBar is the bar" rule; the remaining
    positional children are the body.
    """
    children = ([app_bar] if app_bar is not None else []) + list(body)
    return Component("Scaffold", {"id": id}, children)


# -- Content ------------------------------------------------------------------

def Card(child: Optional[Component] = None, *, id: Optional[str] = None) -> Component:#, elevation=None, padding=None, border_radius=None) -> Component:
    return Component(
        "Card",
        {"id": id},#, "elevation": elevation, "padding": padding, "borderRadius": border_radius},
        [child] if child is not None else None,
    )

def Text(
    value: str,
    *,
    id: Optional[str] = None,
    style: Optional[Literal["body", "caption", "title", "heading", "code"]] = None,
    muted: Optional[bool] = None,
    max_lines: Optional[int | float] = None,
) -> Component:
    return Component(
        "Text",
        {
            "id": id,
            "value": value,
            "style": style,
            "muted": muted,
            "maxLines": max_lines,
        },
    )


def Icon(
    name: MaterialIcon,
    *,
    id: Optional[str] = None,
    size: Optional[int | float] = None,
) -> Component:
    return Component("Icon", {"id": id, "name": _icon(name), "size": size})


def Image(
    src: PluginResource,
    *,
    id: Optional[str] = None,
    width: Optional[int | float] = None,
    height: Optional[int | float] = None,
    fit: Optional[Literal["contain", "cover", "fill", "none"]] = None,
) -> Component:
    if not isinstance(src, PluginResource):
        raise TypeError("Image sources must use plugin.resources.asset(...)")
    return Component(
        "Image",
        {"id": id, "src": str(src), "width": width, "height": height, "fit": fit},
    )


def Video(
    src: PluginResource,
    *,
    id: Optional[str] = None,
    width: Optional[int | float] = None,
    height: Optional[int | float] = None,
    fit: Optional[Literal["contain", "cover", "fill", "none"]] = None,
    autoplay: Optional[bool] = None,
    looping: Optional[bool] = None,
    muted: Optional[bool] = None,
    show_controls: Optional[bool] = None,
) -> Component:
    if not isinstance(src, PluginResource):
        raise TypeError("Video sources must use plugin.resources.asset(...)")
    return Component(
        "Video",
        {
            "id": id,
            "src": str(src),
            "width": width,
            "height": height,
            "fit": fit,
            "autoplay": autoplay,
            "looping": looping,
            "muted": muted,
            "showControls": show_controls,
        },
    )


def Canvas(
    *,
    id: str,
    width: Optional[int | float] = None,
    height: Optional[int | float] = None,
    ops: Any = None,
    interactive: Optional[bool] = None,
    viewport: Optional[dict[Any, Any]] = None,
    on_tap: Optional[Callable[[dict[str, Any]], None]] = None,
    on_drag: Optional[Callable[[dict[str, Any]], None]] = None,
    on_hover: Optional[Callable[[dict[str, Any]], None]] = None,
    on_pointer: Optional[Callable[[dict[str, Any]], None]] = None,
) -> Component:
    """A high-performance interactive custom-draw surface.

    ``ops`` is the persistent base layer (rides snapshot/patch); use the
    :class:`CanvasController` ``push_ops``/``set_ops`` for the ephemeral
    overlay. All four events are opt-in: a handler is wired only when passed,
    producing zero cross-process traffic otherwise. ``id`` is required because
    both invoke and event delivery key on it.
    """
    component = Component(
        "Canvas",
        {
            "id": id,
            "width": width,
            "height": height,
            "ops": ops,
            "interactive": interactive,
            "viewport": viewport,
        },
    )
    if on_tap:
        component.on("tap", on_tap)
    if on_drag:
        component.on("drag", on_drag)
    if on_hover:
        component.on("hover", on_hover)
    if on_pointer:
        component.on("pointer", on_pointer)
    return component


class MarkdownLinkEvent(dict[str, Any]):
    def __init__(self, payload: dict[str, Any]) -> None:
        super().__init__(payload)

    @property
    def href(self) -> str:
        return str(self.get("href", ""))


def Markdown(
    value: str,
    *,
    id: Optional[str] = None,
    on_link_tap: Optional[Callable[[MarkdownLinkEvent], None]] = None,
) -> Component:
    if on_link_tap is not None and not id:
        raise ValueError("Markdown requires id when on_link_tap is set")
    component = Component("Markdown", {"id": id, "value": value})
    if on_link_tap:
        component.on("linkTap", lambda payload: on_link_tap(MarkdownLinkEvent(payload)))
    return component


def CodeBlock(
    code: str,
    *,
    id: Optional[str] = None,
    language: Optional[str] = None,
    show_line_numbers: Optional[bool] = None,
) -> Component:
    return Component(
        "CodeBlock",
        {
            "id": id,
            "code": code,
            "language": language,
            "showLineNumbers": show_line_numbers,
        },
    )


def Badge(
    label: str,
    *,
    id: Optional[str] = None,
    tone: Optional[
        Literal["neutral", "info", "success", "warning", "danger"]
    ] = None,
) -> Component:
    return Component("Badge", {"id": id, "label": label, "tone": tone})


# -- Input --------------------------------------------------------------------


def TextField(
    *,
    id: str,
    value: Optional[str] = None,
    placeholder: Optional[str] = None,
    label: Optional[str] = None,
    enabled: Optional[bool] = None,
    multiline: Optional[bool] = None,
    on_change: Optional[Callable[[dict[str, Any]], None]] = None,
    on_submit: Optional[Callable[[dict[str, Any]], None]] = None,
) -> Component:
    component = Component(
        "TextField",
        {
            "id": id,
            "value": value,
            "placeholder": placeholder,
            "label": label,
            "enabled": enabled,
            "multiline": multiline,
        },
    )
    if on_change:
        component.on("change", on_change)
    if on_submit:
        component.on("submit", on_submit)
    return component


def NumberField(
    *,
    id: str,
    value: Optional[int | float] = None,
    min: Optional[int | float] = None,
    max: Optional[int | float] = None,
    step: Optional[int | float] = None,
    label: Optional[str] = None,
    enabled: Optional[bool] = None,
    on_change: Optional[Callable[[dict[str, Any]], None]] = None,
    on_submit: Optional[Callable[[dict[str, Any]], None]] = None,
) -> Component:
    component = Component(
        "NumberField",
        {
            "id": id,
            "value": value,
            "min": min,
            "max": max,
            "step": step,
            "label": label,
            "enabled": enabled,
        },
    )
    if on_change:
        component.on("change", on_change)
    if on_submit:
        component.on("submit", on_submit)
    return component


def Select(
    *,
    id: str,
    options: list[SelectOption | dict[str, Any]],
    value: Optional[str] = None,
    label: Optional[str] = None,
    enabled: Optional[bool] = None,
    on_change: Optional[Callable[[dict[str, Any]], None]] = None,
) -> Component:
    component = Component(
        "Select",
        {
            "id": id,
            "options": options,
            "value": value,
            "label": label,
            "enabled": enabled,
        },
    )
    if on_change:
        component.on("change", on_change)
    return component


def Checkbox(
    *,
    id: str,
    value: Optional[bool] = None,
    label: Optional[str] = None,
    enabled: Optional[bool] = None,
    on_change: Optional[Callable[[dict[str, Any]], None]] = None,
) -> Component:
    component = Component(
        "Checkbox",
        {"id": id, "value": value, "label": label, "enabled": enabled},
    )
    if on_change:
        component.on("change", on_change)
    return component


def Switch(
    *,
    id: str,
    value: Optional[bool] = None,
    label: Optional[str] = None,
    enabled: Optional[bool] = None,
    on_change: Optional[Callable[[dict[str, Any]], None]] = None,
) -> Component:
    component = Component(
        "Switch",
        {"id": id, "value": value, "label": label, "enabled": enabled},
    )
    if on_change:
        component.on("change", on_change)
    return component


def Slider(
    *,
    id: str,
    value: Optional[int | float] = None,
    min: Optional[int | float] = None,
    max: Optional[int | float] = None,
    step: Optional[int | float] = None,
    enabled: Optional[bool] = None,
    on_change: Optional[Callable[[dict[str, Any]], None]] = None,
) -> Component:
    component = Component(
        "Slider",
        {
            "id": id,
            "value": value,
            "min": min,
            "max": max,
            "step": step,
            "enabled": enabled,
        },
    )
    if on_change:
        component.on("change", on_change)
    return component


# -- Menus --------------------------------------------------------------------


class MenuShortcut(dict[str, Any]):
    """A platform-aware keyboard shortcut shown beside a menu item."""

    def __init__(
        self,
        key: str,
        *,
        primary: bool = False,
        control: bool = False,
        shift: bool = False,
        alt: bool = False,
        meta: bool = False,
    ) -> None:
        super().__init__(
            key=key,
            primary=primary,
            control=control,
            shift=shift,
            alt=alt,
            meta=meta,
        )

    @property
    def key(self) -> str:
        return str(self["key"])


class MenuItem(dict[str, Any]):
    """Typed leaf menu entry."""

    kind: str = "item"

    def __init__(
        self,
        *,
        id: str,
        label: str,
        icon: Optional[MaterialIcon] = None,
        trailing_icon: Optional[MaterialIcon] = None,
        shortcut: Optional[MenuShortcut | dict[str, Any]] = None,
        enabled: Optional[bool] = None,
        visible: Optional[bool] = None,
        tone: Optional[str] = None,
        close_on_select: Optional[bool] = None,
    ) -> None:
        super().__init__(type=self.kind, id=id, label=label)
        _menu_put(self, "icon", _icon(icon))
        _menu_put(self, "trailingIcon", _icon(trailing_icon))
        _menu_put(self, "shortcut", shortcut)
        _menu_put(self, "enabled", enabled)
        _menu_put(self, "visible", visible)
        _menu_put(self, "tone", tone)
        _menu_put(self, "closeOnSelect", close_on_select)

    @property
    def id(self) -> str:
        return str(self["id"])

    @property
    def label(self) -> str:
        return str(self["label"])


class MenuDivider(dict[str, Any]):
    def __init__(self, label: Optional[str] = None) -> None:
        super().__init__(type="divider")
        _menu_put(self, "label", label)


class MenuCheckboxItem(MenuItem):
    kind: str = "checkbox"

    def __init__(self, *, checked: bool = False, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self["checked"] = checked


class MenuRadioItem(MenuItem):
    kind: str = "radio"

    def __init__(self, *, selected: bool = False, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self["selected"] = selected


class Submenu(dict[str, Any]):
    def __init__(
        self,
        *,
        label: str,
        children: Iterable[dict[str, Any]],
        id: Optional[str] = None,
        icon: Optional[MaterialIcon] = None,
        enabled: Optional[bool] = None,
        visible: Optional[bool] = None,
    ) -> None:
        super().__init__(type="submenu", label=label, children=list(children))
        _menu_put(self, "id", id)
        _menu_put(self, "icon", _icon(icon))
        _menu_put(self, "enabled", enabled)
        _menu_put(self, "visible", visible)

    @property
    def id(self) -> Optional[str]:
        value = self.get("id")
        return str(value) if value is not None else None

    @property
    def label(self) -> str:
        return str(self["label"])


class MenuEvent(dict[str, Any]):
    """Payload emitted by a native menu selection."""

    @property
    def item_id(self) -> Optional[str]:
        value = self.get("itemId")
        return str(value) if value is not None else None

    @property
    def item_type(self) -> str:
        return str(self.get("itemType", "item"))

    @property
    def checked(self) -> Optional[bool]:
        value = self.get("checked")
        return bool(value) if value is not None else None

    @property
    def selected(self) -> Optional[bool]:
        value = self.get("selected")
        return bool(value) if value is not None else None

    @property
    def target_id(self) -> Optional[str]:
        value = self.get("targetId")
        return str(value) if value is not None else None

    @property
    def target_type(self) -> Optional[str]:
        value = self.get("targetType")
        return str(value) if value is not None else None


def _menu_put(target: dict[str, Any], key: str, value: Any) -> None:
    if value is not None:
        target[key] = dict(value) if isinstance(value, dict) else value


# -- Actions ------------------------------------------------------------------


def Button(
    *,
    id: str,
    label: str,
    icon: Optional[MaterialIcon] = None,
    variant: Optional[Literal["primary", "secondary", "ghost", "danger"]] = None,
    enabled: Optional[bool] = None,
    on_press: Optional[Callable[[dict[str, Any]], None]] = None,
) -> Component:
    component = Component(
        "Button",
        {
            "id": id,
            "label": label,
            "icon": _icon(icon),
            "variant": variant,
            "enabled": enabled,
        },
    )
    if on_press:
        component.on("press", on_press)
    return component


def IconButton(
    *,
    id: str,
    icon: MaterialIcon,
    tooltip: Optional[str] = None,
    enabled: Optional[bool] = None,
    on_press: Optional[Callable[[dict[str, Any]], None]] = None,
) -> Component:
    component = Component(
        "IconButton",
        {"id": id, "icon": _icon(icon), "tooltip": tooltip, "enabled": enabled},
    )
    if on_press:
        component.on("press", on_press)
    return component


def Menu(
    *,
    id: str,
    items: Iterable[dict[str, Any]],
    label: Optional[str] = None,
    icon: Optional[MaterialIcon] = None,
    tooltip: Optional[str] = None,
    enabled: Optional[bool] = None,
    icon_only: Optional[bool] = None,
    alignment: Optional[
        Literal["bottomStart", "bottomEnd", "topStart", "topEnd"]
    ] = None,
    offset_x: Optional[int | float] = None,
    offset_y: Optional[int | float] = None,
    use_root_overlay: Optional[bool] = None,
    child: Optional[Component] = None,
    on_select: Optional[Callable[[MenuEvent], None]] = None,
) -> Component:
    component = Component(
        "Menu",
        {
            "id": id,
            "items": list(items),
            "label": label,
            "icon": _icon(icon),
            "tooltip": tooltip,
            "enabled": enabled,
            "iconOnly": icon_only,
            "alignment": alignment,
            "offsetX": offset_x,
            "offsetY": offset_y,
            "useRootOverlay": use_root_overlay,
        },
        [child] if child is not None else None,
    )
    if on_select:
        component.on("select", lambda payload: on_select(MenuEvent(payload)))
    return component


def MenuBar(
    *,
    id: str,
    items: Iterable[dict[str, Any]],
    on_select: Optional[Callable[[MenuEvent], None]] = None,
) -> Component:
    component = Component("MenuBar", {"id": id, "items": list(items)})
    if on_select:
        component.on("select", lambda payload: on_select(MenuEvent(payload)))
    return component


def ContextMenu(
    child: Optional[Component] = None,
    *,
    id: str,
    items: Iterable[dict[str, Any]],
    enabled: Optional[bool] = None,
    on_select: Optional[Callable[[MenuEvent], None]] = None,
) -> Component:
    component = Component(
        "ContextMenu",
        {"id": id, "items": list(items), "enabled": enabled},
        [child] if child is not None else None,
    )
    if on_select:
        component.on("select", lambda payload: on_select(MenuEvent(payload)))
    return component


def _bind_context_menu_provider(
    component: Component,
    entries: Optional[Iterable[dict[str, Any]]],
    provider: Optional[Callable[..., Any]],
) -> None:
    if provider is None:
        return
    by_id = {
        str(entry.id if isinstance(entry, DataItem) else entry.get("id")): entry
        for entry in entries or ()
        if isinstance(entry, dict) and entry.get("id") is not None
    }

    def request_menu(payload: dict[str, Any]) -> Any:
        target = by_id.get(str(payload.get("targetId", "")))
        return None if target is None else provider(target)

    component.on("contextMenuRequest", request_menu)


def _items_by_id(
    entries: Optional[Iterable[dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    return {
        str(entry.id if isinstance(entry, DataItem) else entry.get("id")): entry
        for entry in entries or ()
        if isinstance(entry, dict) and entry.get("id") is not None
    }


def _bind_item_event(
    component: Component,
    event: str,
    entries: Optional[Iterable[dict[str, Any]]],
    payload_key: str,
    handler: Optional[Callable[..., Any]],
) -> None:
    if handler is None:
        return
    by_id = _items_by_id(entries)

    def dispatch(payload: dict[str, Any]) -> Any:
        item = by_id.get(str(payload.get(payload_key, "")))
        if item is not None:
            return handler(item)
        return None

    component.on(event, dispatch)


def Dropdown(
    *,
    id: str,
    items: list[dict[str, Any]],
    label: Optional[str] = None,
    on_select: Optional[Callable[[dict[str, Any]], None]] = None,
) -> Component:
    component = Component("Dropdown", {"id": id, "items": items, "label": label})
    if on_select:
        component.on("select", on_select)
    return component


def Dialog(
    *children: Component,
    id: str,
    title: Optional[str] = None,
    open: Optional[bool] = None,
    on_close: Optional[Callable[[dict[str, Any]], None]] = None,
) -> Component:
    component = Component(
        "Dialog", {"id": id, "title": title, "open": open}, list(children)
    )
    if on_close:
        component.on("close", on_close)
    return component


def Tooltip(
    child: Optional[Component] = None,
    *,
    id: Optional[str] = None,
    message: str,
) -> Component:
    return Component(
        "Tooltip",
        {"id": id, "message": message},
        [child] if child is not None else None,
    )


# -- Data ---------------------------------------------------------------------


def VirtualList(
    *,
    id: str,
    items: Optional[list[ListItem | dict[str, Any]]] = None,
    item_count: Optional[int | float] = None,
    item_height: Optional[int | float] = None,
    selected_id: Optional[str] = None,
    empty_label: Optional[str] = None,
    on_select: Optional[Callable[[ListItem | dict[str, Any]], None]] = None,
    on_activate: Optional[Callable[[ListItem | dict[str, Any]], None]] = None,
    on_request_range: Optional[Callable[[RangeRequest], None]] = None,
    on_context_menu: Optional[
        Callable[
            [ListItem | dict[str, Any]],
            Component | Awaitable[Component] | None,
        ]
    ] = None,
) -> Component:
    component = Component(
        "VirtualList",
        {
            "id": id,
            "items": items,
            "itemCount": item_count,
            "itemHeight": item_height,
            "selectedId": selected_id,
            "emptyLabel": empty_label,
        },
    )
    _bind_item_event(component, "select", items, "itemId", on_select)
    _bind_item_event(component, "activate", items, "itemId", on_activate)
    if on_request_range:
        component.on(
            "requestRange", lambda payload: on_request_range(RangeRequest(payload))
        )
    _bind_context_menu_provider(component, items, on_context_menu)
    return component


def TreeView(
    *,
    id: str,
    nodes: Optional[list[TreeNode | dict[str, Any]]] = None,
    expanded_ids: Optional[list[str]] = None,
    selected_id: Optional[str] = None,
    indent: Optional[int | float] = None,
    searchable: Optional[bool] = None,
    empty_label: Optional[str] = None,
    on_select: Optional[Callable[[TreeNode | dict[str, Any]], None]] = None,
    on_activate: Optional[Callable[[TreeNode | dict[str, Any]], None]] = None,
    on_expand: Optional[Callable[[TreeNode | dict[str, Any]], None]] = None,
    on_collapse: Optional[Callable[[TreeNode | dict[str, Any]], None]] = None,
    on_request_children: Optional[
        Callable[[TreeNode | dict[str, Any]], None]
    ] = None,
    on_context_menu: Optional[
        Callable[
            [TreeNode | dict[str, Any]],
            Component | Awaitable[Component] | None,
        ]
    ] = None,
) -> Component:
    component = Component(
        "TreeView",
        {
            "id": id,
            "nodes": nodes,
            "expandedIds": expanded_ids,
            "selectedId": selected_id,
            "indent": indent,
            "searchable": searchable,
            "emptyLabel": empty_label,
        },
    )
    for event, handler in (
        ("select", on_select),
        ("activate", on_activate),
        ("expand", on_expand),
        ("collapse", on_collapse),
        ("requestChildren", on_request_children),
    ):
        _bind_item_event(component, event, nodes, "nodeId", handler)
    _bind_context_menu_provider(component, nodes, on_context_menu)
    return component


def DataTable(
    *,
    id: str,
    columns: list[TableColumn | dict[str, Any]],
    rows: Optional[list[TableRow | dict[str, Any]]] = None,
    row_count: Optional[int | float] = None,
    row_height: Optional[int | float] = None,
    show_header: Optional[bool] = None,
    selected_id: Optional[str] = None,
    sort_column: Optional[str] = None,
    sort_ascending: Optional[bool] = None,
    empty_label: Optional[str] = None,
    on_select: Optional[Callable[[TableRow | dict[str, Any]], None]] = None,
    on_activate: Optional[Callable[[TableRow | dict[str, Any]], None]] = None,
    on_sort: Optional[Callable[[TableColumn | dict[str, Any]], None]] = None,
    on_request_range: Optional[Callable[[RangeRequest], None]] = None,
    on_context_menu: Optional[
        Callable[
            [TableRow | dict[str, Any]],
            Component | Awaitable[Component] | None,
        ]
    ] = None,
) -> Component:
    component = Component(
        "DataTable",
        {
            "id": id,
            "columns": columns,
            "rows": rows,
            "rowCount": row_count,
            "rowHeight": row_height,
            "showHeader": show_header,
            "selectedId": selected_id,
            "sortColumn": sort_column,
            "sortAscending": sort_ascending,
            "emptyLabel": empty_label,
        },
    )
    _bind_item_event(component, "select", rows, "rowId", on_select)
    _bind_item_event(component, "activate", rows, "rowId", on_activate)
    _bind_item_event(component, "sort", columns, "columnId", on_sort)
    if on_request_range:
        component.on(
            "requestRange", lambda payload: on_request_range(RangeRequest(payload))
        )
    _bind_context_menu_provider(component, rows, on_context_menu)
    return component


def PropertyGrid(
    *,
    id: str,
    entries: list[PropertyEntry | dict[str, Any]],
    on_select: Optional[
        Callable[[PropertyEntry | dict[str, Any]], None]
    ] = None,
    on_expand: Optional[
        Callable[[PropertyEntry | dict[str, Any]], None]
    ] = None,
) -> Component:
    component = Component("PropertyGrid", {"id": id, "entries": entries})
    _bind_item_event(component, "select", entries, "nodeId", on_select)
    _bind_item_event(component, "expand", entries, "nodeId", on_expand)
    return component
