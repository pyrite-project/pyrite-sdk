"""Typed builders for renderer-driven native plugin views.

The transport remains dictionary-based, but plugin authors work with named
objects and a view facade.  This keeps renderer protocol details such as
``role``, ``parentId`` and patch revisions out of ordinary plugin code.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Awaitable, Callable, Iterable, Optional, TYPE_CHECKING

from .icons import Icons, MaterialIcon

if TYPE_CHECKING:
    from .components import Component
    from .view import ViewInstance


EventHandler = Callable[[dict[str, Any]], None]


class ChildrenState(str, Enum):
    unloaded = "unloaded"
    loading = "loading"
    loaded = "loaded"
    error = "error"


class IconColor(str, Enum):
    primary = "primary"
    secondary = "secondary"
    tertiary = "tertiary"
    muted = "muted"
    error = "error"


def _value(value: Any) -> Any:
    if isinstance(value, MaterialIcon):
        return str(value)
    return value.value if isinstance(value, Enum) else value


def _put(node: dict[str, Any], key: str, value: Any) -> None:
    if key == "icon" and value is not None and not isinstance(value, MaterialIcon):
        raise TypeError("icon values must use pyrite_sdk.api.icons.Icons")
    value = _value(value)
    if value is not None:
        node[key] = value


class NativeViewNode(dict[str, Any]):
    """Base class for typed renderer data that serializes as a wire node."""

    @property
    def id(self) -> str:
        return self["id"]

    @property
    def parent_id(self) -> Optional[str]:
        return self.get("parentId")

    @property
    def label(self) -> str:
        return str(self.get("label", self.get("name", "")))

    @property
    def icon(self) -> Optional[str]:
        value = self.get("icon")
        return str(value) if value is not None else None

    @property
    def icon_color(self) -> Optional[str]:
        value = self.get("iconColor")
        return str(value) if value is not None else None

    @property
    def has_children(self) -> bool:
        return bool(self.get("hasChildren", False))

    @property
    def children_state(self) -> Optional[str]:
        value = self.get("childrenState")
        return str(value) if value is not None else None

    @property
    def role(self) -> Optional[str]:
        value = self.get("role")
        return str(value) if value is not None else None


class TreeItem(NativeViewNode):
    def __init__(
        self,
        *,
        id: str,
        label: str,
        parent_id: Optional[str] = None,
        icon: Optional[MaterialIcon] = None,
        has_children: bool = False,
        children_state: str | ChildrenState = ChildrenState.loaded,
        **metadata: Any,
    ) -> None:
        super().__init__(
            id=id,
            label=label,
            parentId=parent_id,
            hasChildren=has_children,
            **metadata,
        )
        _put(self, "icon", icon)
        _put(self, "childrenState", children_state)


class VirtualListItem(NativeViewNode):
    def __init__(
        self,
        *,
        id: str,
        label: str,
        icon: Optional[MaterialIcon] = None,
        **metadata: Any,
    ) -> None:
        super().__init__(id=id, label=label, **metadata)
        _put(self, "icon", icon)


class TableRowItem(NativeViewNode):
    def __init__(
        self, *, id: str, cells: dict[str, Any], **metadata: Any
    ) -> None:
        super().__init__(id=id, cells=dict(cells), **metadata)

    @property
    def cells(self) -> dict[str, Any]:
        return dict(self.get("cells") or {})


class TableColumn(dict[str, Any]):
    def __init__(
        self,
        *,
        id: str,
        label: str,
        width: Optional[float] = None,
        flex: Optional[int] = None,
        frozen: Optional[bool] = None,
        sortable: Optional[bool] = None,
    ) -> None:
        super().__init__(id=id, label=label)
        _put(self, "width", width)
        _put(self, "flex", flex)
        _put(self, "frozen", frozen)
        _put(self, "sortable", sortable)

    @property
    def id(self) -> str:
        return str(self["id"])

    @property
    def label(self) -> str:
        return str(self["label"])


class FormField(NativeViewNode):
    def __init__(
        self,
        *,
        id: str,
        label: str,
        value: Any = None,
        kind: str = "text",
        options: Optional[Iterable[dict[str, Any]]] = None,
    ) -> None:
        super().__init__(id=id, label=label, kind=kind, value=value)
        if options is not None:
            self["options"] = list(options)

    @property
    def value(self) -> Any:
        return self.get("value")

    @property
    def kind(self) -> str:
        return str(self.get("kind", "text"))


class MarkdownContent(NativeViewNode):
    def __init__(self, text: str, *, id: str = "content") -> None:
        super().__init__(id=id, text=text)

    @property
    def text(self) -> str:
        return str(self.get("text", ""))


class LogEntry(VirtualListItem):
    def __init__(
        self,
        *,
        id: str,
        message: str,
        level: str = "info",
        timestamp: Optional[str] = None,
    ) -> None:
        super().__init__(id=id, label=message, level=level, timestamp=timestamp)

    @property
    def message(self) -> str:
        return self.label

    @property
    def level(self) -> str:
        return str(self.get("level", "info"))


class OutlineItem(NativeViewNode):
    def __init__(
        self,
        *,
        id: str,
        label: str,
        parent_id: Optional[str] = None,
        icon: Optional[MaterialIcon] = None,
        icon_color: Optional[str | IconColor] = None,
        has_children: bool = False,
        children_state: str | ChildrenState = ChildrenState.loaded,
        kind: Optional[int | str] = None,
        detail: Optional[str] = None,
        line: Optional[int] = None,
        column: Optional[int] = None,
    ) -> None:
        super().__init__(
            id=id,
            label=label,
            parentId=parent_id,
            hasChildren=has_children,
        )
        _put(self, "icon", icon)
        _put(self, "iconColor", icon_color)
        _put(self, "childrenState", children_state)
        _put(self, "kind", kind)
        _put(self, "detail", detail)
        _put(self, "line", line)
        _put(self, "column", column)

    @property
    def kind(self) -> Optional[int | str]:
        return self.get("kind")

    @property
    def detail(self) -> Optional[str]:
        value = self.get("detail")
        return str(value) if value is not None else None

    @property
    def line(self) -> Optional[int]:
        value = self.get("line")
        return int(value) if value is not None else None

    @property
    def column(self) -> Optional[int]:
        value = self.get("column")
        return int(value) if value is not None else None


class VariableEntry(NativeViewNode):
    def __init__(
        self,
        *,
        id: str,
        name: str,
        type_name: str = "",
        value: str = "",
        parent_id: Optional[str] = None,
        icon: Optional[MaterialIcon] = None,
        icon_color: Optional[str | IconColor] = None,
        has_children: bool = False,
        children_state: str | ChildrenState = ChildrenState.loaded,
    ) -> None:
        super().__init__(
            id=id,
            name=name,
            type=type_name,
            repr=value,
            hasChildren=has_children,
        )
        _put(self, "parentId", parent_id)
        _put(self, "icon", icon)
        _put(self, "iconColor", icon_color)
        _put(self, "childrenState", children_state)

    @property
    def name(self) -> str:
        return str(self.get("name", ""))

    @property
    def type_name(self) -> str:
        return str(self.get("type", ""))

    @property
    def value(self) -> str:
        return str(self.get("repr", ""))

    def update_fields(
        self,
        *,
        value: Optional[str] = None,
        icon: Optional[MaterialIcon] = None,
        icon_color: Optional[str | IconColor] = None,
        children_state: Optional[str | ChildrenState] = None,
    ) -> None:
        _put(self, "repr", value)
        _put(self, "icon", icon)
        _put(self, "iconColor", icon_color)
        _put(self, "childrenState", children_state)


class VariableScope(VariableEntry):
    def __init__(
        self,
        *,
        id: str,
        name: str,
        error: Optional[str] = None,
        has_children: bool = False,
    ) -> None:
        super().__init__(
            id=id,
            name=name,
            type_name="scope",
            value=error or "",
            icon=Icons.error_outline if error else Icons.data_object,
            icon_color=IconColor.error if error else IconColor.primary,
            has_children=has_children,
        )


class LoadMoreEntry(VariableEntry):
    def __init__(
        self,
        *,
        id: str,
        parent_id: str,
        progress: str,
        label: str = "Load more...",
    ) -> None:
        super().__init__(
            id=id,
            parent_id=parent_id,
            name=label,
            value=progress,
            icon=Icons.more_horiz,
            icon_color=IconColor.muted,
        )
        self["role"] = "loadMore"


class ViewPlaceholder(NativeViewNode):
    def __init__(
        self,
        *,
        state: str,
        label: str,
        icon: MaterialIcon = Icons.info_outline,
        icon_color: Optional[str | IconColor] = None,
    ) -> None:
        super().__init__(
            id=f"state:{state}",
            name=label,
            label=label,
            type="",
            repr="",
            icon=icon,
            hasChildren=False,
            childrenState=ChildrenState.loaded.value,
            state=state,
            role="placeholder",
        )
        _put(self, "iconColor", icon_color)


class ViewAction:
    """An AppBar action whose transport representation is SDK-private."""

    def __init__(
        self,
        *,
        id: str,
        label: str,
        icon: MaterialIcon,
        on_trigger: EventHandler,
    ) -> None:
        if not isinstance(icon, MaterialIcon):
            raise TypeError("icon values must use pyrite_sdk.api.icons.Icons")
        self.id: str = id
        self.label: str = label
        self.icon: MaterialIcon = icon
        self.on_trigger: EventHandler = on_trigger

    def _to_node(self, title: str) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.label,
            "label": self.label,
            "type": "",
            "repr": "",
            "icon": self.icon,
            "hasChildren": False,
            "childrenState": ChildrenState.loaded.value,
            "role": "appBarAction",
            "appBarTitle": title,
        }


class ViewMenuAction(ViewAction):
    """An AppBar action that opens a declarative native menu."""

    def __init__(
        self,
        *,
        id: str,
        label: str,
        items: Iterable[dict[str, Any]],
        icon: MaterialIcon = Icons.more_vert,
        on_trigger: EventHandler,
    ) -> None:
        super().__init__(id=id, label=label, icon=icon, on_trigger=on_trigger)
        self.items: list[dict[str, Any]] = list(items)

    def _to_node(self, title: str) -> dict[str, Any]:
        node = super()._to_node(title)
        node["role"] = "appBarMenu"
        node["items"] = self.items
        return node


class RendererView:
    """High-level facade for one renderer-driven view instance."""

    def __init__(
        self,
        model: "ViewInstance",
        *,
        title: str,
        actions: Iterable[ViewAction] = (),
    ) -> None:
        self.model: ViewInstance = model
        self.title: str = title
        self._actions: list[ViewAction] = list(actions)
        self._items: list[NativeViewNode] = []
        self._props: dict[str, Any] = {}
        self._rendered_nodes: list[dict[str, Any]] = []
        self._select_handler: Optional[Callable[[NativeViewNode], None]] = None
        self._activate_handler: Optional[Callable[[NativeViewNode], None]] = None
        self._request_children_handler: Optional[
            Callable[[NativeViewNode], None]
        ] = None
        self._context_menu_handler: Optional[
            Callable[
                [NativeViewNode],
                Component | Awaitable[Optional[Component]] | None,
            ]
        ] = None
        model.on_event(model.view_id, "select", self._handle_select)
        model.on_event(model.view_id, "activate", self._handle_activate)
        model.on_event(
            model.view_id,
            "requestChildren",
            self._handle_request_children,
        )
        model.on_event(
            model.view_id,
            "contextMenuRequest",
            self._handle_context_menu_request,
        )

    @property
    def view_id(self) -> str:
        return self.model.view_id

    @property
    def instance_id(self) -> str:
        return self.model.instance_id

    @property
    def visible(self) -> bool:
        return self.model.visible

    @property
    def items(self) -> list[NativeViewNode]:
        return list(self._items)

    @property
    def nodes(self) -> list[dict[str, Any]]:
        return [dict(node) for node in self._rendered_nodes]

    def open(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self.model.open(callback=callback)

    def close(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self.model.close(callback=callback)

    def on_visibility(
        self, handler: Callable[[bool], None]
    ) -> Callable[[bool], None]:
        return self.model.on_visibility(handler)

    def on_select(
        self, handler: Callable[[NativeViewNode], None]
    ) -> Callable[[NativeViewNode], None]:
        self._select_handler = handler
        return handler

    def on_activate(
        self, handler: Callable[[NativeViewNode], None]
    ) -> Callable[[NativeViewNode], None]:
        self._activate_handler = handler
        return handler

    def on_request_children(
        self, handler: Callable[[NativeViewNode], None]
    ) -> Callable[[NativeViewNode], None]:
        self._request_children_handler = handler
        return handler

    def on_context_menu(
        self,
        handler: Callable[
            [NativeViewNode],
            Component | Awaitable[Optional[Component]] | None,
        ],
    ) -> Callable[
        [NativeViewNode],
        Component | Awaitable[Optional[Component]] | None,
    ]:
        self._context_menu_handler = handler
        if self.model.revision > 0:
            self._publish()
        return handler

    def set_actions(self, actions: Iterable[ViewAction]) -> None:
        self._actions = list(actions)
        if self.model.revision > 0:
            self._publish()

    def set_props(self, **props: Any) -> None:
        self._props.update({key: value for key, value in props.items() if value is not None})
        if self.model.revision > 0:
            self._publish()

    def set_items(self, items: Iterable[NativeViewNode]) -> None:
        values = list(items)
        if not all(isinstance(item, NativeViewNode) for item in values):
            raise TypeError("renderer views require typed NativeViewNode items")
        self._items = values
        self._publish()

    def show_placeholder(
        self,
        label: str,
        *,
        state: str = "empty",
        icon: MaterialIcon = Icons.info_outline,
        icon_color: Optional[str | IconColor] = None,
    ) -> None:
        self.set_items(
            [
                ViewPlaceholder(
                    state=state,
                    label=label,
                    icon=icon,
                    icon_color=icon_color,
                )
            ]
        )

    def _handle_select(self, payload: dict[str, Any]) -> None:
        node_id = str(
            payload.get("nodeId")
            or payload.get("entryId")
            or payload.get("itemId")
            or ""
        )
        action = next((item for item in self._actions if item.id == node_id), None)
        if action is not None:
            action.on_trigger(payload)
        elif self._select_handler is not None:
            item = self._item_by_id(node_id)
            if item is not None:
                self._select_handler(item)

    def _handle_activate(self, payload: dict[str, Any]) -> None:
        item = self._item_from_payload(payload)
        if self._activate_handler is not None and item is not None:
            self._activate_handler(item)

    def _handle_request_children(self, payload: dict[str, Any]) -> None:
        item = self._item_from_payload(payload)
        if self._request_children_handler is not None and item is not None:
            self._request_children_handler(item)

    def _handle_context_menu_request(
        self, payload: dict[str, Any]
    ) -> Component | Awaitable[Optional[Component]] | None:
        if self._context_menu_handler is None:
            return None
        target_id = str(payload.get("targetId", ""))
        item = next((item for item in self._items if item.id == target_id), None)
        return None if item is None else self._context_menu_handler(item)

    def _item_from_payload(
        self, payload: dict[str, Any]
    ) -> Optional[NativeViewNode]:
        node_id = str(
            payload.get("nodeId")
            or payload.get("entryId")
            or payload.get("itemId")
            or payload.get("rowId")
            or ""
        )
        return self._item_by_id(node_id)

    def _item_by_id(self, node_id: str) -> Optional[NativeViewNode]:
        return next((item for item in self._items if item.id == node_id), None)

    def _publish(self) -> None:
        nodes = [dict(item) for item in self._items]
        if self._props:
            nodes.append(
                {
                    "id": "__view_config__",
                    "label": "",
                    "role": "viewConfig",
                    "props": dict(self._props),
                }
            )
        nodes.extend(action._to_node(self.title) for action in self._actions)
        if self._context_menu_handler is not None:
            nodes.append(
                {
                    "id": "__context_menu_provider__",
                    "name": "",
                    "label": "",
                    "type": "",
                    "repr": "",
                    "hasChildren": False,
                    "childrenState": ChildrenState.loaded.value,
                    "role": "contextMenuProvider",
                }
            )
        self._replace_nodes(nodes)

    def _replace_nodes(self, nodes: list[dict[str, Any]]) -> None:
        copied = [dict(node) for node in nodes]
        if self.model.revision == 0:
            self.model.snapshot(copied)
            self._rendered_nodes = copied
            return

        old_by_id = {node["id"]: node for node in self._rendered_nodes}
        new_by_id = {node["id"]: node for node in copied}
        working = [node["id"] for node in self._rendered_nodes]
        with self.model.batch():
            for node_id in list(reversed(working)):
                if node_id not in new_by_id:
                    self.model.remove(node_id)
                    working.remove(node_id)
            for index, node in enumerate(copied):
                node_id = node["id"]
                if node_id not in working:
                    self.model.insert(node_id, node, index=index)
                    working.insert(index, node_id)
                    continue
                current_index = working.index(node_id)
                if current_index != index:
                    self.model.move(node_id, index)
                    working.pop(current_index)
                    working.insert(index, node_id)
                if old_by_id.get(node_id) != node:
                    self.model.update(node_id, node)
        self._rendered_nodes = copied


class OutlineView(RendererView):
    pass


class VariableInspectorView(RendererView):
    pass


class TreeView(RendererView):
    def configure(
        self,
        *,
        expanded_ids: Optional[Iterable[str]] = None,
        selected_id: Optional[str] = None,
        indent: Optional[float] = None,
        searchable: Optional[bool] = None,
        empty_label: Optional[str] = None,
    ) -> None:
        self.set_props(
            expandedIds=list(expanded_ids) if expanded_ids is not None else None,
            selectedId=selected_id,
            indent=indent,
            searchable=searchable,
            emptyLabel=empty_label,
        )


class VirtualListView(RendererView):
    def configure(
        self,
        *,
        item_count: Optional[int] = None,
        item_height: Optional[float] = None,
        selected_id: Optional[str] = None,
        empty_label: Optional[str] = None,
    ) -> None:
        self.set_props(
            itemCount=item_count,
            itemHeight=item_height,
            selectedId=selected_id,
            emptyLabel=empty_label,
        )


class TableView(RendererView):
    @property
    def columns(self) -> list[TableColumn]:
        return list(self._props.get("columns") or [])

    def set_columns(self, columns: Iterable[TableColumn]) -> None:
        values = list(columns)
        if not all(isinstance(column, TableColumn) for column in values):
            raise TypeError("table views require typed TableColumn values")
        self.set_props(columns=values)

    def configure(
        self,
        *,
        row_count: Optional[int] = None,
        row_height: Optional[float] = None,
        show_header: Optional[bool] = None,
        selected_id: Optional[str] = None,
        sort_column: Optional[str] = None,
        sort_ascending: Optional[bool] = None,
        empty_label: Optional[str] = None,
    ) -> None:
        self.set_props(
            rowCount=row_count,
            rowHeight=row_height,
            showHeader=show_header,
            selectedId=selected_id,
            sortColumn=sort_column,
            sortAscending=sort_ascending,
            emptyLabel=empty_label,
        )


class FormView(RendererView):
    pass


class MarkdownView(RendererView):
    def set_markdown(self, value: str) -> None:
        self.set_items([MarkdownContent(value)])

    def on_link_tap(self, handler: Callable[[str], None]) -> Callable[[str], None]:
        self.model.on_event(
            self.model.view_id,
            "linkTap",
            lambda payload: handler(str(payload.get("href", ""))),
        )
        return handler


class LogView(RendererView):
    def configure(
        self,
        *,
        item_height: Optional[float] = None,
        empty_label: Optional[str] = None,
    ) -> None:
        self.set_props(itemHeight=item_height, emptyLabel=empty_label)

    def append(self, entry: LogEntry) -> None:
        if not isinstance(entry, LogEntry):
            raise TypeError("log views require LogEntry values")
        self.set_items([*self._items, entry])

    def extend(self, entries: Iterable[LogEntry]) -> None:
        values = list(entries)
        if not all(isinstance(entry, LogEntry) for entry in values):
            raise TypeError("log views require LogEntry values")
        self.set_items([*self._items, *values])

    def clear(self) -> None:
        self.set_items([])


__all__ = [
    "ChildrenState",
    "IconColor",
    "FormField",
    "FormView",
    "LoadMoreEntry",
    "LogEntry",
    "LogView",
    "MarkdownContent",
    "MarkdownView",
    "NativeViewNode",
    "OutlineItem",
    "OutlineView",
    "RendererView",
    "TableColumn",
    "TableRowItem",
    "TableView",
    "TreeItem",
    "TreeView",
    "VariableEntry",
    "VariableInspectorView",
    "VariableScope",
    "VirtualListItem",
    "VirtualListView",
    "ViewAction",
    "ViewMenuAction",
    "ViewPlaceholder",
]
