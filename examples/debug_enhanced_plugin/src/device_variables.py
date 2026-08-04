from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
from time import monotonic
from typing import Any, Mapping, Optional

from pyrite_sdk.api.components import ContextMenu, MenuItem
from pyrite_sdk.api.icons import Icons, MaterialIcon
from pyrite_sdk.api.native_views import (
    ChildrenState,
    IconColor,
    LoadMoreEntry,
    VariableEntry,
    VariableInspectorView,
    VariableScope,
    ViewAction,
    ViewPlaceholder,
)
from pyrite_sdk.api.runtime import RuntimeUnavailableError, StaleReferenceError


VARIABLES_VIEW_ID = "debug-enhanced.device-variables"
SIDEBAR_INSTANCE_ID = "container:debug-enhanced"
OPEN_MAIN_TAB_ID = "action:open-device-variables-main"
OPEN_EXPANSION_TAB_ID = "action:open-device-variables-expansion"
REFRESH_COMMAND_ID = "debug-enhanced.refreshVariables"
SHOW_PRIVATE_CONFIG_ID = "debug-enhanced.showPrivate"
PAGE_SIZE = 100
MAX_REPR_CHARS = 2_000


@dataclass(frozen=True)
class _PageRequest:
    kind: str
    parent_id: str
    start: int
    session_id: Optional[str] = None
    scope_id: Optional[str] = None
    reference: Optional[str] = None


def _stable_id(*parts: object) -> str:
    raw = "/".join(str(part) for part in parts)
    return sha1(raw.encode("utf-8")).hexdigest()[:20]


def _short_repr(value: str) -> str:
    if len(value) <= MAX_REPR_CHARS:
        return value
    return value[: MAX_REPR_CHARS - 3] + "..."


def _variable_appearance(type_name: str) -> tuple[MaterialIcon, str]:
    normalized = type_name.rsplit(".", 1)[-1].lower()
    if normalized in {"list", "tuple", "set", "frozenset", "array"}:
        return Icons.data_array, "primary"
    if normalized in {"dict", "mapping", "object"}:
        return Icons.category_outlined, "tertiary"
    if normalized in {"str", "bytes", "bytearray", "memoryview"}:
        return Icons.text_fields, "tertiary"
    if normalized in {"int", "float", "complex"}:
        return Icons.tag, "primary"
    if normalized == "bool":
        return Icons.toggle_on_outlined, "secondary"
    if normalized in {"nonetype", "null"}:
        return Icons.block, "muted"
    if normalized in {"function", "method", "builtin_function_or_method"}:
        return Icons.functions, "secondary"
    if normalized in {"module", "type", "class"}:
        return (
            (
                Icons.view_module_outlined
                if normalized == "module"
                else Icons.class_outlined
            ),
            "primary",
        )
    return Icons.data_object, "muted"


class DeviceVariablesController:
    """Browses variables reported by the connected device runtime.

    The controller never evaluates code itself. All reads go through the
    structured runtime inspection API, whose host declines with ``unavailable``
    when it cannot inspect without interrupting the user's program.
    """

    def __init__(
        self,
        runtime,
        view: VariableInspectorView,
        *,
        tabs=None,
        views=None,
        clipboard=None,
        configuration=None,
    ) -> None:
        self.runtime = runtime
        self.view = view
        self.tabs = tabs
        self.views = views
        self.clipboard = clipboard
        self.configuration = configuration
        self.session_id: Optional[str] = None
        self.generation: Optional[int] = None
        self._epoch = 0
        self._paused = False
        self._refresh_pending = False
        self._show_private = False
        self._subscriptions = []
        self._views: dict[str, VariableInspectorView] = {}
        self._visible_models = {}
        self._content_nodes: list[VariableEntry | ViewPlaceholder] = []
        self._rendered_nodes: list[dict[str, Any]] = []
        self._references: dict[str, str] = {}
        self._pages: dict[str, _PageRequest] = {}
        self._tab_error: Optional[str] = None
        self._last_action: dict[str, float] = {}

    def start(self) -> None:
        self._attach_view(self.view)
        self._replace_nodes([self._placeholder("loading", "正在读取设备变量...")])
        self._subscriptions.extend(
            [
                self.runtime.on_session_created(self._on_runtime_event),
                self.runtime.on_session_state_changed(self._on_runtime_event),
                self.runtime.on_program_paused(self._on_runtime_event),
                self.runtime.on_program_finished(self._on_runtime_event),
                self.runtime.on_backend_restarted(self._on_backend_restarted),
                self.runtime.on_variables_changed(self._on_runtime_event),
                self.runtime.on_session_ended(self._on_session_ended),
            ]
        )
        if self.configuration is not None:
            self._subscriptions.append(
                self.configuration.on_changed(
                    self._on_configuration_changed,
                    configuration_id=SHOW_PRIVATE_CONFIG_ID,
                )
            )
            self.configuration.get(
                SHOW_PRIVATE_CONFIG_ID,
                callback=self._on_show_private_loaded,
            )
        self.refresh()

    def _on_show_private_loaded(self, data=None, error=None, **_) -> None:
        if error is not None or not isinstance(data, dict):
            return
        self._show_private = bool(data.get("value"))
        self.refresh(silent=True)

    def _on_configuration_changed(self, event: Mapping[str, Any]) -> None:
        if event.get("id") != SHOW_PRIVATE_CONFIG_ID:
            return
        self._show_private = bool(event.get("value"))
        self.refresh(silent=True)

    def _include_variable(self, name: str) -> bool:
        if self._show_private:
            return True
        return not name.startswith("_")

    def dispose(self) -> None:
        self._epoch += 1
        for subscription in self._subscriptions:
            subscription.dispose()
        self._subscriptions.clear()
        for view in self._views.values():
            view.close()
        self._views.clear()
        self._visible_models.clear()
        self._clear_references()

    def set_visible(self, visible: bool) -> None:
        self._paused = not visible
        if self._paused:
            self._epoch += 1
            self._refresh_pending = True
        elif self._refresh_pending and self._can_refresh():
            self.refresh(silent=True)

    def refresh(self, *, silent: bool = False) -> None:
        if not self._can_refresh():
            self._refresh_pending = True
            return
        self._epoch += 1
        epoch = self._epoch
        self._refresh_pending = False
        if not silent:
            self._replace_nodes([self._placeholder("loading", "正在读取设备变量...")])
        self.runtime.sessions(
            callback=lambda sessions=None, error=None, **_: self._on_sessions(
                epoch, sessions or [], error
            )
        )

    def _on_sessions(self, epoch: int, sessions: list, error=None) -> None:
        if not self._is_current(epoch):
            return
        if error is not None:
            self._show_error(error)
            return
        if not sessions:
            self.session_id = None
            self.generation = None
            self._clear_references()
            self._replace_nodes(
                [self._placeholder("disconnected", "连接设备后可查看设备变量")]
            )
            return

        session = next(
            (item for item in sessions if item.session_id == "device"), sessions[0]
        )
        if (
            self.session_id != session.session_id
            or self.generation != session.generation
        ):
            self._clear_references()
            self._replace_nodes([self._placeholder("loading", "正在读取设备变量...")])
        self.session_id = session.session_id
        self.generation = session.generation

        if session.program_state == "running":
            self._replace_nodes(
                [
                    self._placeholder(
                        "running",
                        "设备程序正在运行；为避免中断程序，变量检查暂不可用",
                    )
                ]
            )
            return
        if session.capability == "unavailable":
            self._replace_nodes(
                [
                    self._placeholder(
                        "unavailable",
                        "当前设备后端暂不支持安全的变量检查",
                    )
                ]
            )
            return

        self.runtime.scopes(
            session.session_id,
            callback=lambda scopes=None, error=None, **_: self._on_scopes(
                epoch, scopes or [], error
            ),
        )

    def _on_scopes(self, epoch: int, scopes: list, error=None) -> None:
        if not self._is_current(epoch):
            return
        if error is not None:
            self._show_error(error)
            return
        if not scopes:
            self._replace_nodes(
                [self._placeholder("empty", "设备没有可检查的变量作用域")]
            )
            return

        pending = len(scopes)
        pages: dict[int, tuple[object, object, object]] = {}

        def complete(index: int, scope, page=None, error=None, **_) -> None:
            nonlocal pending
            if not self._is_current(epoch):
                return
            pages[index] = (scope, page, error)
            pending -= 1
            if pending == 0:
                self._publish_scope_pages(epoch, pages)

        for index, scope in enumerate(scopes):
            self.runtime.variables(
                self.session_id,
                scope.id,
                start=0,
                count=PAGE_SIZE,
                callback=lambda page=None, error=None, index=index, scope=scope, **_: complete(
                    index, scope, page, error
                ),
            )

    def _publish_scope_pages(self, epoch: int, pages: dict) -> None:
        if not self._is_current(epoch):
            return
        nodes: list[VariableEntry] = []
        self._clear_references()
        for index in sorted(pages):
            scope, page, error = pages[index]
            scope_node_id = (
                f"scope:{_stable_id(self.session_id, self.generation, scope.id)}"
            )
            nodes.append(
                VariableScope(
                    id=scope_node_id,
                    name=self._scope_name(scope.name),
                    error=None if error is None else str(error),
                    has_children=bool(page and page.items),
                )
            )
            if error is not None or page is None:
                continue
            nodes.extend(self._variable_nodes(page.items, scope_node_id, page.start))
            self._append_more_node(
                nodes,
                parent_id=scope_node_id,
                page=page,
                request=_PageRequest(
                    kind="scope",
                    parent_id=scope_node_id,
                    start=page.start + len(page.items),
                    session_id=self.session_id,
                    scope_id=scope.id,
                ),
            )
        self._replace_nodes(nodes or [self._placeholder("empty", "设备变量为空")])

    def _on_request_children(self, node: VariableEntry) -> None:
        node_id = node.id
        reference = self._references.get(node_id)
        if reference is None or not self._can_refresh():
            return
        epoch = self._epoch
        self._update_node(node_id, children_state=ChildrenState.loading)
        self.runtime.children(
            reference,
            start=0,
            count=PAGE_SIZE,
            callback=lambda page=None, error=None, **_: self._on_children(
                epoch, node_id, reference, page, error
            ),
        )

    def _on_children(self, epoch, parent_id, reference, page, error=None) -> None:
        if not self._is_current(epoch) or self._references.get(parent_id) != reference:
            return
        if error is not None:
            if isinstance(error, StaleReferenceError):
                self._on_backend_restarted({})
            else:
                self._update_node(parent_id, children_state=ChildrenState.error)
            return
        self._remove_children(parent_id)
        self._update_node(parent_id, children_state=ChildrenState.loaded)
        if page is not None:
            self._content_nodes.extend(
                self._variable_nodes(page.items, parent_id, page.start)
            )
            self._append_more_node(
                self._content_nodes,
                parent_id=parent_id,
                page=page,
                request=_PageRequest(
                    kind="children",
                    parent_id=parent_id,
                    start=page.start + len(page.items),
                    reference=reference,
                ),
            )
        self._publish_nodes()

    def _on_select(self, node: VariableEntry) -> None:
        node_id = node.id
        request = self._pages.get(node_id)
        if request is not None:
            self._request_next_page(node_id, request)

    def _request_next_page(self, node_id: str, request: _PageRequest) -> None:
        epoch = self._epoch

        def complete(page=None, error=None, **_) -> None:
            if not self._is_current(epoch) or self._pages.get(node_id) != request:
                return
            if error is not None:
                if isinstance(error, StaleReferenceError):
                    self._on_backend_restarted({})
                else:
                    self._update_node(
                        node_id, value=str(error), icon=Icons.error_outline
                    )
                return
            self._pages.pop(node_id, None)
            self._content_nodes = [
                node for node in self._content_nodes if node.id != node_id
            ]
            if page is not None:
                self._content_nodes.extend(
                    self._variable_nodes(page.items, request.parent_id, page.start)
                )
                self._append_more_node(
                    self._content_nodes,
                    parent_id=request.parent_id,
                    page=page,
                    request=_PageRequest(
                        kind=request.kind,
                        parent_id=request.parent_id,
                        start=page.start + len(page.items),
                        session_id=request.session_id,
                        scope_id=request.scope_id,
                        reference=request.reference,
                    ),
                )
            self._publish_nodes()

        if request.kind == "scope":
            self.runtime.variables(
                request.session_id,
                request.scope_id,
                start=request.start,
                count=PAGE_SIZE,
                callback=complete,
            )
        else:
            self.runtime.children(
                request.reference,
                start=request.start,
                count=PAGE_SIZE,
                callback=complete,
            )

    def _variable_nodes(
        self,
        variables,
        parent_id: str,
        start: int,
    ) -> list[VariableEntry]:
        nodes: list[VariableEntry] = []
        for offset, variable in enumerate(variables):
            if not self._include_variable(variable.name):
                continue
            identity = _stable_id(
                self.session_id,
                self.generation,
                parent_id,
                variable.name,
                start + offset,
            )
            node_id = f"variable:{identity}"
            icon, color = _variable_appearance(variable.type)
            has_children = bool(variable.has_children and variable.reference)
            nodes.append(
                VariableEntry(
                    id=node_id,
                    parent_id=parent_id,
                    name=variable.name,
                    type_name=variable.type,
                    value=_short_repr(variable.repr),
                    icon=icon,
                    icon_color=color,
                    has_children=has_children,
                    children_state=(
                        ChildrenState.unloaded if has_children else ChildrenState.loaded
                    ),
                )
            )
            if has_children:
                self._references[node_id] = variable.reference
        return nodes

    def _append_more_node(self, nodes, *, parent_id, page, request) -> None:
        total = page.total
        next_start = page.start + len(page.items)
        if total is None or next_start >= total:
            return
        node_id = f"page:{_stable_id(parent_id, next_start)}"
        nodes.append(
            LoadMoreEntry(
                id=node_id,
                parent_id=parent_id,
                label="加载更多...",
                progress=f"{next_start}/{total}",
            )
        )
        self._pages[node_id] = request

    def _remove_children(self, parent_id: str) -> None:
        child_ids: set[str] = set()
        pending = [parent_id]
        while pending:
            current = pending.pop()
            direct = [
                node.id for node in self._content_nodes if node.parent_id == current
            ]
            child_ids.update(direct)
            pending.extend(direct)
        self._content_nodes = [
            node for node in self._content_nodes if node.id not in child_ids
        ]
        for child_id in child_ids:
            self._references.pop(child_id, None)
            self._pages.pop(child_id, None)

    def _on_runtime_event(self, _event: dict) -> None:
        self.refresh(silent=True)

    def _on_backend_restarted(self, _event: dict) -> None:
        self._epoch += 1
        self._clear_references()
        self.session_id = None
        self.generation = None
        self.refresh()

    def _on_session_ended(self, _event: dict) -> None:
        self._epoch += 1
        self._clear_references()
        self.session_id = None
        self.generation = None
        self._replace_nodes(
            [self._placeholder("disconnected", "连接设备后可查看设备变量")]
        )

    def _show_error(self, error) -> None:
        if isinstance(error, RuntimeUnavailableError):
            message = "当前设备后端暂不支持安全的变量检查"
            state = "unavailable"
        else:
            message = f"读取设备变量失败：{error}"
            state = "error"
        self._replace_nodes([self._placeholder(state, message)])

    def _attach_view(self, view: VariableInspectorView) -> None:
        instance_id = view.instance_id
        self._views[instance_id] = view
        self._visible_models[instance_id] = view.visible
        view.set_actions(self._actions())
        view.on_select(self._on_select)
        view.on_request_children(self._on_request_children)
        view.on_context_menu(self._context_menu)
        view.on_visibility(
            lambda visible, instance_id=instance_id: self._on_visibility(
                instance_id, visible
            )
        )
        view.open()
        if self._content_nodes:
            view.set_items(self._published_items())

    def _open_tab(self, action_id: str, *, expansion: bool) -> None:
        if self.tabs is None or self.views is None:
            return
        now = monotonic()
        if now - self._last_action.get(action_id, 0.0) < 0.35:
            return
        self._last_action[action_id] = now
        self.tabs.create_view(
            VARIABLES_VIEW_ID,
            title="设备变量",
            expansion=expansion,
            callback=self._on_tab_created,
        )

    def _on_tab_created(self, instance=None, error=None, **_) -> None:
        if error is not None:
            self._tab_error = f"无法创建设备变量标签页：{error}"
            self._publish_nodes()
            return
        if instance is None or not instance.instance_id or self.views is None:
            self._tab_error = "无法创建设备变量标签页：宿主响应无效"
            self._publish_nodes()
            return
        self._tab_error = None
        self._publish_nodes()
        self._attach_view(
            self.views.variable_inspector(
                VARIABLES_VIEW_ID,
                instance_id=instance.instance_id,
                title="设备变量",
            )
        )

    def _on_visibility(self, instance_id: str, visible: bool) -> None:
        self._visible_models[instance_id] = visible
        if visible and self._refresh_pending:
            self.refresh(silent=True)
        elif not self._can_refresh():
            self._epoch += 1
            self._refresh_pending = True

    def _context_menu(self, node: VariableEntry) -> ContextMenu:
        items = []
        if node.role == "loadMore":
            items.append(
                MenuItem(id="loadMore", label="加载更多", icon=Icons.more_horiz)
            )
        elif node.type_name != "scope":
            items.append(MenuItem(id="copy", label="复制", icon=Icons.copy))
        return ContextMenu(
            id=f"variables-menu:{node.id}",
            items=items,
            on_select=lambda event: self._on_context_menu_select(node, event),
        )

    def _on_context_menu_select(self, node: VariableEntry, event) -> None:
        if event.item_id == "loadMore":
            self._on_select(node)
        elif event.item_id == "copy":
            if self.clipboard is not None:
                self.clipboard.set_text(node.value)

    def _can_refresh(self) -> bool:
        return not self._paused and any(self._visible_models.values())

    def _is_current(self, epoch: int) -> bool:
        return epoch == self._epoch and self._can_refresh()

    def _clear_references(self) -> None:
        self._references.clear()
        self._pages.clear()

    def _update_node(self, node_id: str, **changes) -> None:
        for node in self._content_nodes:
            if node.id == node_id and isinstance(node, VariableEntry):
                node.update_fields(**changes)
                break
        self._publish_nodes()

    @staticmethod
    def _scope_name(name: str) -> str:
        return {
            "globals": "全局变量",
            "locals": "局部变量",
            "nonlocals": "非局部变量",
        }.get(name.lower(), name)

    @staticmethod
    def _placeholder(state: str, label: str) -> ViewPlaceholder:
        is_error = state == "error"
        return ViewPlaceholder(
            state=state,
            label=label,
            icon=Icons.error_outline if is_error else Icons.power_off_outlined,
            icon_color=IconColor.error if is_error else IconColor.muted,
        )

    def _actions(self) -> list[ViewAction]:
        return [
            ViewAction(
                id=OPEN_MAIN_TAB_ID,
                label="在主编辑区打开设备变量",
                icon=Icons.open_in_new,
                on_trigger=lambda _: self._open_tab(
                    OPEN_MAIN_TAB_ID,
                    expansion=False,
                ),
            ),
            ViewAction(
                id=OPEN_EXPANSION_TAB_ID,
                label="在拓展区打开设备变量",
                icon=Icons.vertical_split_outlined,
                on_trigger=lambda _: self._open_tab(
                    OPEN_EXPANSION_TAB_ID,
                    expansion=True,
                ),
            ),
        ]

    def _replace_nodes(
        self,
        nodes: list[VariableEntry | ViewPlaceholder],
    ) -> None:
        self._content_nodes = list(nodes)
        self._publish_nodes()

    def _publish_nodes(self) -> None:
        nodes = self._published_items()
        for view in self._views.values():
            view.set_items(nodes)
        self._rendered_nodes = self.view.nodes

    def _published_items(self) -> list[VariableEntry | ViewPlaceholder]:
        nodes = list(self._content_nodes)
        if self._tab_error is not None:
            nodes.append(self._placeholder("tab-error", self._tab_error))
        return nodes
