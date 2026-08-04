from __future__ import annotations

import re
from hashlib import sha1
from time import monotonic
from typing import Any, Optional

from pyrite_sdk.api.components import ContextMenu, MenuDivider, MenuItem
from pyrite_sdk.api.document import Document, DocumentSymbol, SymbolResult
from pyrite_sdk.api.icons import Icons, MaterialIcon
from pyrite_sdk.api.native_views import (
    IconColor,
    OutlineItem,
    OutlineView,
    ViewAction,
    ViewPlaceholder,
)
from pyrite_sdk.core.plugin import UiPlugin

try:
    from .device_variables import DeviceVariablesController, VARIABLES_VIEW_ID
except ImportError:
    from device_variables import DeviceVariablesController, VARIABLES_VIEW_ID


PLUGIN_ID = "debug-enhanced"
OUTLINE_VIEW_ID = "debug-enhanced.outline"
SIDEBAR_INSTANCE_ID = "container:debug-enhanced"
OPEN_EXPANSION_TAB_ID = "action:open-expansion-tab"
MAX_SOURCE_BYTES = 1024 * 1024
MAX_SOURCE_LINES = 20_000

_DEFINITION_PATTERN = re.compile(
    r"^(?P<indent>[ \t]*)(?:async[ \t]+)?"
    r"(?P<type>def|class)[ \t]+(?P<name>[^\W\d]\w*)"
)


class SourceTooLargeError(ValueError):
    pass


def _raw_range(raw: dict) -> Optional[tuple[tuple[int, int], tuple[int, int]]]:
    location = raw.get("location")
    location_range = location.get("range") if isinstance(location, dict) else None
    symbol_range = raw.get("range") or location_range or raw.get("selectionRange")
    if not isinstance(symbol_range, dict):
        return None
    start = symbol_range.get("start")
    end = symbol_range.get("end")
    if not isinstance(start, dict) or not isinstance(end, dict):
        return None
    return (
        (int(start.get("line", 0)), int(start.get("character", 0))),
        (int(end.get("line", 0)), int(end.get("character", 0))),
    )


def _symbol_start(raw: dict) -> tuple[int, int]:
    location = raw.get("location")
    location_range = location.get("range") if isinstance(location, dict) else None
    symbol_range = raw.get("selectionRange") or raw.get("range") or location_range
    start = symbol_range.get("start") if isinstance(symbol_range, dict) else None
    if not isinstance(start, dict):
        return 0, 0
    return int(start.get("line", 0)), int(start.get("character", 0))


def _strictly_contains(
    outer: tuple[tuple[int, int], tuple[int, int]],
    inner: tuple[tuple[int, int], tuple[int, int]],
) -> bool:
    return outer != inner and outer[0] <= inner[0] and outer[1] >= inner[1]


def rebuild_flat_symbol_tree(
    symbols: list[DocumentSymbol],
) -> list[DocumentSymbol]:
    """Rebuild hierarchy for flat LSP SymbolInformation responses."""
    if not symbols or not all(
        isinstance(symbol.raw.get("location"), dict) for symbol in symbols
    ):
        return symbols

    rebuilt = [
        DocumentSymbol(
            name=symbol.name,
            kind=symbol.kind,
            detail=symbol.detail,
            children=[],
            raw=symbol.raw,
        )
        for symbol in symbols
    ]
    ranges = [_raw_range(symbol.raw) for symbol in symbols]
    parents: list[Optional[int]] = [None] * len(symbols)

    for child_index, child in enumerate(symbols):
        child_range = ranges[child_index]
        enclosing: list[int] = []
        if child_range is not None:
            enclosing = [
                index
                for index, candidate_range in enumerate(ranges)
                if index != child_index
                and candidate_range is not None
                and _strictly_contains(candidate_range, child_range)
            ]
        if enclosing:
            parents[child_index] = min(
                enclosing,
                key=lambda index: (
                    ranges[index][1][0] - ranges[index][0][0],
                    ranges[index][1][1] - ranges[index][0][1],
                ),
            )
            continue

        container_name = child.raw.get("containerName")
        if container_name:
            matches = [
                index
                for index in range(child_index)
                if symbols[index].name == container_name
            ]
            if matches:
                parents[child_index] = matches[-1]

    roots: list[DocumentSymbol] = []
    for index, symbol in enumerate(rebuilt):
        parent_index = parents[index]
        if parent_index is None:
            roots.append(symbol)
        else:
            rebuilt[parent_index].children.append(symbol)
    return roots


def scan_python_outline(
    source: str,
    *,
    max_bytes: int = MAX_SOURCE_BYTES,
    max_lines: int = MAX_SOURCE_LINES,
) -> list[DocumentSymbol]:
    """Parse class/function structure without requiring syntactically valid code."""
    byte_count = len(source.encode("utf-8"))
    line_count = source.count("\n") + (1 if source else 0)
    if byte_count > max_bytes or line_count > max_lines:
        raise SourceTooLargeError(
            f"source is {byte_count} bytes / {line_count} lines; "
            f"limit is {max_bytes} bytes / {max_lines} lines"
        )

    roots: list[DocumentSymbol] = []
    stack: list[tuple[int, DocumentSymbol]] = []
    for line_number, line in enumerate(source.splitlines()):
        match = _DEFINITION_PATTERN.match(line)
        if match is None:
            continue
        indent = len(match.group("indent").expandtabs(8))
        while stack and indent <= stack[-1][0]:
            stack.pop()

        definition_type = match.group("type")
        parent = stack[-1][1] if stack else None
        kind = (
            5
            if definition_type == "class"
            else (6 if parent and parent.kind == 5 else 12)
        )
        column = len(match.group("indent"))
        name = match.group("name")
        symbol = DocumentSymbol.from_json(
            {
                "name": name,
                "kind": kind,
                "detail": definition_type,
                "range": {
                    "start": {"line": line_number, "character": column},
                    "end": {
                        "line": line_number,
                        "character": column + len(name),
                    },
                },
                "selectionRange": {
                    "start": {"line": line_number, "character": column},
                    "end": {
                        "line": line_number,
                        "character": column + len(name),
                    },
                },
            }
        )
        if parent is None:
            roots.append(symbol)
        else:
            parent.children.append(symbol)
        stack.append((indent, symbol))
    return roots


def _symbol_icon(kind: int) -> MaterialIcon:
    return {
        1: Icons.description_outlined,
        2: Icons.view_module_outlined,
        3: Icons.account_tree_outlined,
        4: Icons.inventory_2_outlined,
        5: Icons.class_outlined,
        6: Icons.functions,
        7: Icons.tune,
        8: Icons.data_object_outlined,
        9: Icons.add_box_outlined,
        10: Icons.format_list_numbered,
        11: Icons.integration_instructions_outlined,
        12: Icons.code,
        13: Icons.data_object,
        14: Icons.lock_outline,
        15: Icons.text_fields,
        16: Icons.tag,
        17: Icons.toggle_on_outlined,
        18: Icons.data_array,
        19: Icons.category_outlined,
        20: Icons.key_outlined,
        21: Icons.block,
        22: Icons.label_outline,
        23: Icons.schema_outlined,
        24: Icons.bolt_outlined,
        25: Icons.calculate_outlined,
        26: Icons.type_specimen_outlined,
    }.get(kind, Icons.code)


def _symbol_color(kind: int) -> str:
    if kind in {2, 3, 4, 10, 22, 24}:
        return "tertiary"
    if kind in {5, 11, 23, 26}:
        return "primary"
    if kind in {6, 9, 12, 25}:
        return "secondary"
    return "muted"


def map_symbol_tree(
    symbols: list[DocumentSymbol],
) -> tuple[list[OutlineItem], dict[str, tuple[int, int]]]:
    """Flatten symbols into stable, parent-linked native tree nodes."""
    nodes: list[OutlineItem] = []
    locations: dict[str, tuple[int, int]] = {}

    def visit(
        symbol: DocumentSymbol,
        parent_id: Optional[str],
        ancestry: str,
        occurrence: int,
    ) -> None:
        line, column = _symbol_start(symbol.raw)
        identity = (
            f"{ancestry}/{symbol.kind}:{symbol.name}:{line}:{column}:{occurrence}"
        )
        node_id = f"symbol:{sha1(identity.encode('utf-8')).hexdigest()[:20]}"
        locations[node_id] = (line, column)
        nodes.append(
            OutlineItem(
                id=node_id,
                label=symbol.name,
                parent_id=parent_id,
                icon=_symbol_icon(symbol.kind),
                icon_color=_symbol_color(symbol.kind),
                has_children=bool(symbol.children),
                kind=symbol.kind,
                detail=symbol.detail,
                line=line,
                column=column,
            )
        )
        duplicates: dict[tuple[int, str, int, int], int] = {}
        for child in symbol.children:
            child_line, child_column = _symbol_start(child.raw)
            key = (child.kind, child.name, child_line, child_column)
            child_occurrence = duplicates.get(key, 0)
            duplicates[key] = child_occurrence + 1
            visit(child, node_id, identity, child_occurrence)

    roots: dict[tuple[int, str, int, int], int] = {}
    for symbol in rebuild_flat_symbol_tree(symbols):
        line, column = _symbol_start(symbol.raw)
        key = (symbol.kind, symbol.name, line, column)
        occurrence = roots.get(key, 0)
        roots[key] = occurrence + 1
        visit(symbol, None, "root", occurrence)
    return nodes, locations


class OutlineController:
    """Coordinates document events, fallback parsing, and all outline views."""

    def __init__(self, documents, view: OutlineView, *, tabs=None, views=None) -> None:
        self.documents = documents
        self.view = view
        self.tabs = tabs
        self.views = views
        self.document: Optional[Document] = None
        self._request_epoch = 0
        self._paused = False
        self._refresh_pending = False
        self._subscriptions = []
        self._views: dict[str, OutlineView] = {}
        self._visible_models = {}
        self._content_nodes: list[OutlineItem | ViewPlaceholder] = []
        self._rendered_nodes: list[dict[str, Any]] = []
        self._locations: dict[str, tuple[int, int]] = {}
        self._tab_error: Optional[str] = None
        self._last_action: dict[str, float] = {}

    def start(self) -> None:
        self._attach_view(self.view)
        self._replace_nodes([self._state_node("loading", "Parsing outline...")])
        self._subscriptions.extend(
            [
                self.documents.on_active_changed(self._on_active_changed),
                self.documents.on_changed(
                    self._on_document_changed,
                    delivery="debounce",
                    debounce_ms=100,
                ),
                self.documents.on_saved(self._on_document_changed),
            ]
        )
        self.documents.get_active(callback=self._on_active_query)

    def dispose(self) -> None:
        self._request_epoch += 1
        for subscription in self._subscriptions:
            subscription.dispose()
        self._subscriptions.clear()
        for view in self._views.values():
            view.close()
        self._views.clear()
        self._visible_models.clear()

    def set_visible(self, visible: bool) -> None:
        if self._paused == (not visible):
            return
        self._paused = not visible
        if self._paused:
            self._request_epoch += 1
            self._refresh_pending = self.document is not None
        elif self._refresh_pending and self._can_refresh():
            self._request_symbols()

    def _attach_view(self, view: OutlineView) -> None:
        instance_id = view.instance_id
        if instance_id in self._views:
            return
        self._views[instance_id] = view
        self._visible_models[instance_id] = view.visible
        view.set_actions(self._actions())
        view.on_select(self._on_select)
        view.on_activate(self._on_reveal)
        view.on_context_menu(self._context_menu)
        view.on_visibility(
            lambda visible, instance_id=instance_id: self._on_visibility(
                instance_id, visible
            )
        )
        view.open()
        if self._content_nodes:
            view.set_items(self._published_items())

    def _on_visibility(self, instance_id: str, visible: bool) -> None:
        self._visible_models[instance_id] = visible
        if not self._can_refresh():
            self._request_epoch += 1
            self._refresh_pending = self.document is not None
        elif self._refresh_pending and self.document is not None:
            self._request_symbols()

    def _can_refresh(self) -> bool:
        return not self._paused and any(self._visible_models.values())

    def _on_active_query(self, document=None, error=None, **_) -> None:
        if error is not None:
            self._replace_nodes([self._state_node("error", str(error))])
            return
        self._set_active_document(document)

    def _on_active_changed(self, event: dict) -> None:
        document_id = event.get("documentId")
        if not document_id:
            self._set_active_document(None)
            return
        self._set_active_document(Document.from_json({**event, "isActive": True}))

    def _on_document_changed(self, event: dict) -> None:
        if self.document is None:
            return
        if event.get("documentId") != self.document.document_id:
            return
        if not self._can_refresh():
            self._refresh_pending = True
            return
        self._request_symbols()

    def _set_active_document(self, document: Optional[Document]) -> None:
        self._request_epoch += 1
        self.document = document
        self._locations = {}
        self._refresh_pending = False
        if document is None:
            self._replace_nodes(
                [
                    self._state_node(
                        "no-document",
                        "请打开或切换到文本文件以查看大纲",
                    )
                ]
            )
            return
        self._replace_nodes([self._state_node("loading", "Parsing outline...")])
        if self._can_refresh():
            self._request_symbols()
        else:
            self._refresh_pending = True

    def _request_symbols(self) -> None:
        document = self.document
        if document is None or not self._can_refresh():
            self._refresh_pending = document is not None
            return
        self._request_epoch += 1
        epoch = self._request_epoch
        document_id = document.document_id
        self._refresh_pending = False

        def complete(result=None, error=None, **_) -> None:
            if not self._is_current(epoch, document_id):
                return
            if error is not None:
                if "unavailable" in str(error).lower():
                    self._request_source(epoch, document_id)
                else:
                    self._replace_nodes(
                        [self._state_node("error", f"Outline error: {error}")]
                    )
                return
            if not isinstance(result, SymbolResult):
                self._replace_nodes(
                    [self._state_node("error", "Invalid symbol result")]
                )
                return
            if result.stale or (
                result.document_id and result.document_id != document_id
            ):
                return
            if not result.symbols:
                self._request_source(epoch, document_id)
                return
            nodes, locations = map_symbol_tree(result.symbols)
            self._locations = locations
            self._replace_nodes(nodes)

        self.documents.symbols(document_id, callback=complete)

    def _request_source(self, epoch: int, document_id: str) -> None:
        def complete(document=None, error=None, **_) -> None:
            if not self._is_current(epoch, document_id):
                return
            if error is not None or document is None or document.text is None:
                message = str(error) if error is not None else "source is unavailable"
                self._replace_nodes(
                    [self._state_node("unavailable", f"Outline unavailable: {message}")]
                )
                return
            try:
                symbols = scan_python_outline(document.text)
            except SourceTooLargeError:
                self._replace_nodes(
                    [
                        self._state_node(
                            "too-large",
                            "File too large for outline (limit 1 MiB / 20,000 lines)",
                        )
                    ]
                )
                return
            nodes, locations = map_symbol_tree(symbols)
            self._locations = locations
            self._replace_nodes(nodes or [self._state_node("empty", "No symbols")])

        self.documents.get(document_id, callback=complete)

    def _is_current(self, epoch: int, document_id: str) -> bool:
        return (
            epoch == self._request_epoch
            and self._can_refresh()
            and self.document is not None
            and self.document.document_id == document_id
        )

    def _on_select(self, node: OutlineItem) -> None:
        self._on_reveal(node)

    def _context_menu(self, node: OutlineItem) -> ContextMenu:
        return ContextMenu(
            id=f"outline-menu:{node.id}",
            items=[
                MenuItem(
                    id="reveal",
                    label=f"跳转到 {node.label}",
                    icon=Icons.open_in_new,
                ),
                MenuDivider(),
                MenuItem(id="refresh", label="刷新大纲", icon=Icons.refresh),
            ],
            on_select=lambda event: self._on_context_menu_select(node, event),
        )

    def _on_context_menu_select(self, node: OutlineItem, event) -> None:
        if event.item_id == "reveal":
            self._on_reveal(node)
        elif event.item_id == "refresh" and self._can_refresh():
            self._request_symbols()

    def _open_tab(self, *, expansion: bool) -> None:
        if self.tabs is None or self.views is None:
            return
        now = monotonic()
        action_id = OPEN_EXPANSION_TAB_ID
        if now - self._last_action.get(action_id, 0.0) < 0.35:
            return
        self._last_action[action_id] = now
        self.tabs.create_view(
            OUTLINE_VIEW_ID,
            title="大纲",
            expansion=expansion,
            callback=self._on_tab_created,
        )

    def _on_tab_created(self, instance=None, error=None, **_) -> None:
        if error is not None:
            self._tab_error = f"Unable to create outline tab: {error}"
            self._publish_nodes()
            return
        if instance is None or not instance.instance_id or self.views is None:
            self._tab_error = "Unable to create outline tab: invalid host response"
            self._publish_nodes()
            return
        self._tab_error = None
        self._publish_nodes()
        self._attach_view(
            self.views.outline(
                OUTLINE_VIEW_ID,
                instance_id=instance.instance_id,
                title="大纲",
            )
        )

    def _on_reveal(self, node: OutlineItem) -> None:
        if self.document is None:
            return
        location = self._locations.get(node.id)
        if location is None:
            return
        self.documents.reveal(
            self.document.document_id,
            location[0],
            column=location[1],
        )

    @staticmethod
    def _state_node(state: str, label: str) -> ViewPlaceholder:
        is_error = state in {"error", "tab-error"}
        return ViewPlaceholder(
            state=state,
            label=label,
            icon=Icons.error_outline if is_error else Icons.code,
            icon_color=IconColor.error if is_error else IconColor.muted,
        )

    def _actions(self) -> list[ViewAction]:
        return [
            ViewAction(
                id=OPEN_EXPANSION_TAB_ID,
                label="在拓展区打开大纲",
                icon=Icons.vertical_split_outlined,
                on_trigger=lambda _: self._open_tab(expansion=True),
            ),
        ]

    def _replace_nodes(self, nodes: list[OutlineItem | ViewPlaceholder]) -> None:
        self._content_nodes = list(nodes)
        self._publish_nodes()

    def _published_items(self) -> list[OutlineItem | ViewPlaceholder]:
        nodes = list(self._content_nodes)
        if self._tab_error is not None:
            nodes.append(self._state_node("tab-error", self._tab_error))
        return nodes

    def _publish_nodes(self) -> None:
        nodes = self._published_items()
        for view in self._views.values():
            view.set_items(nodes)
        self._rendered_nodes = self.view.nodes


class DebugEnhancedPlugin(UiPlugin):
    def __init__(self) -> None:
        super().__init__()
        self.outline = None
        self.device_variables = None

    def on_start(self) -> None:
        outline_view = self.views.outline(
            OUTLINE_VIEW_ID,
            instance_id=SIDEBAR_INSTANCE_ID,
            title="大纲",
        )
        self.outline = OutlineController(
            self.documents,
            outline_view,
            tabs=self.tabs,
            views=self.views,
        )
        self.outline.start()
        variables_view = self.views.variable_inspector(
            VARIABLES_VIEW_ID,
            instance_id=SIDEBAR_INSTANCE_ID,
            title="设备变量",
        )
        self.device_variables = DeviceVariablesController(
            self.runtime,
            variables_view,
            tabs=self.tabs,
            views=self.views,
            clipboard=self.clipboard,
            configuration=self.configuration,
        )
        self.device_variables.start()
        self.commands.register(
            "debug-enhanced.refreshVariables",
            lambda args=None, context=None: self.device_variables.refresh(),
        )

    def on_pause(self) -> None:
        if self.outline is not None:
            self.outline.set_visible(False)
        if self.device_variables is not None:
            self.device_variables.set_visible(False)

    def on_resume(self) -> None:
        if self.outline is not None:
            self.outline.set_visible(True)
        if self.device_variables is not None:
            self.device_variables.set_visible(True)

    def on_dispose(self) -> None:
        if self.outline is not None:
            self.outline.dispose()
        if self.device_variables is not None:
            self.device_variables.dispose()
