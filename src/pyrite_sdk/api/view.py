from __future__ import annotations

import inspect
import json
from contextlib import contextmanager
from typing import Any, Callable, Optional, TYPE_CHECKING
from uuid import uuid4

from ..models.schema import request
from .components import (
    Component,
    _bind_component_value,
    _wire_component_value,
    collect_handlers,
)

if TYPE_CHECKING:
    from ..core.bridge import Bridge


MAX_SNAPSHOT_NODES = 20_000
MAX_PATCH_OPS = 2_000
MAX_VIEW_PAYLOAD_BYTES = 2 * 1024 * 1024


class ViewProtocolError(Exception):
    """Raised when a view operation is invalid before it reaches the host."""


class PatchOp:
    """One operation in a patch transaction."""

    __slots__ = ("op", "id", "index", "data")

    def __init__(
        self,
        op: str,
        id: str,
        index: Optional[int] = None,
        data: Optional[dict] = None,
    ):
        self.op = op
        self.id = id
        self.index = index
        self.data = data

    def to_json(self) -> dict:
        payload: dict[str, Any] = {"op": self.op, "id": self.id}
        if self.index is not None:
            payload["index"] = self.index
        if self.data is not None:
            payload["data"] = _wire_component_value(self.data)
        return payload


class ViewModel:
    """Local mirror of one view instance's model, with revision tracking.

    Sends a full snapshot first, then incremental patches. At most one patch is
    in flight: operations produced while waiting for an ack are merged into the
    next patch, so a fast producer cannot outrun the host.
    """

    def __init__(
        self,
        bridge: "Bridge",
        view_id: str,
        instance_id: Optional[str] = None,
    ):
        self._bridge = bridge
        self.view_id = view_id
        self.instance_id = instance_id or uuid4().hex
        self.revision = 0
        self._nodes: list[dict] = []
        self._pending: list[PatchOp] = []
        self._in_flight: Optional[int] = None
        self._closed = False
        self._batch_depth = 0
        # Routing is per view instance: the host owns the authoritative stack and
        # pushes it back on ide.view.route.sync, so these mirror the last sync.
        self._route = "home"
        self._route_stack: list[str] = ["home"]
        self._route_params: dict = {}
        self._route_handlers: list[Callable] = []
        # (component_id, event) -> handler, rebuilt from the component tree on
        # every snapshot/patch so a removed component's handler goes with it.
        self._handlers: dict[tuple[str, str], Callable] = {}
        self._transient_handlers: dict[tuple[str, str], Callable] = {}
        # Renderer-driven views send plain data nodes rather than a component
        # tree. Their root events are registered explicitly and survive model
        # snapshots, unlike handlers collected from component nodes.
        self._explicit_handlers: dict[tuple[str, str], Callable] = {}
        self._visible = True
        self._needs_snapshot = False
        self._visibility_handlers: list[Callable[[bool], None]] = []

    # -- Identity -----------------------------------------------------------

    def _keys(self) -> dict:
        return {"viewId": self.view_id, "instanceId": self.instance_id}

    @property
    def nodes(self) -> list[dict]:
        return list(self._nodes)

    @property
    def has_in_flight(self) -> bool:
        return self._in_flight is not None

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    # -- Lifecycle ----------------------------------------------------------

    def open(self, callback: Optional[Callable] = None) -> None:
        self._bridge.push_wait_response(
            request("sdk.view.open", payload=self._keys()), callback=callback
        )

    def close(self, callback: Optional[Callable] = None) -> None:
        self._closed = True
        self._pending.clear()
        self._in_flight = None
        self._bridge.push_wait_response(
            request("sdk.view.close", payload=self._keys()), callback=callback
        )

    def snapshot(
        self,
        nodes: list[dict],
        revision: Optional[int] = None,
        callback: Optional[Callable] = None,
    ) -> None:
        """Sends a full snapshot and resets local patch state."""
        if self._closed:
            raise ViewProtocolError("view is closed")
        if len(nodes) > MAX_SNAPSHOT_NODES:
            raise ViewProtocolError(
                f"snapshot exceeds {MAX_SNAPSHOT_NODES} nodes"
            )
        # Component instances are preserved (not copied into plain dicts) so
        # _wire_nodes can still reduce their handlers to markers; a raw function
        # reaching the transport would fail to serialize.
        self._nodes = [n if isinstance(n, Component) else dict(n) for n in nodes]
        for node in self._nodes:
            _bind_component_value(node, self)
        self.revision = 1 if revision is None else revision
        self._pending.clear()
        self._in_flight = None
        # Rebuild the handler table from this snapshot, so handlers for nodes
        # that are gone do not linger.
        self._handlers = collect_handlers(nodes)
        self._transient_handlers.clear()
        payload = {
            **self._keys(),
            "revision": self.revision,
            "nodes": self._wire_nodes(),
        }
        if (
            len(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
            > MAX_VIEW_PAYLOAD_BYTES
        ):
            raise ViewProtocolError(
                f"snapshot exceeds {MAX_VIEW_PAYLOAD_BYTES} bytes"
            )
        self._needs_snapshot = False
        self._bridge.push_wait_response(
            request(
                "sdk.view.snapshot",
                payload=payload,
            ),
            callback=callback,
        )

    def _wire_nodes(self) -> list:
        """Nodes in wire form, with component handlers reduced to markers."""
        return [_wire_component_value(node) for node in self._nodes]

    def dispatch_event(
        self, component_id: str, event: str, payload: Optional[dict] = None
    ) -> bool:
        """Invokes the handler for a component event; True when one ran."""
        handler = self._explicit_handlers.get(
            (component_id, event),
            self._handlers.get(
                (component_id, event),
                self._transient_handlers.get((component_id, event)),
            ),
        )
        if handler is None:
            return False
        handler(payload or {})
        return True

    async def request_context_menu(
        self, component_id: str, payload: Optional[dict] = None
    ) -> Optional[dict]:
        """Invokes a row menu provider and returns its ContextMenu wire node."""
        handler = self._explicit_handlers.get(
            (component_id, "contextMenuRequest"),
            self._handlers.get((component_id, "contextMenuRequest")),
        )
        if handler is None:
            return None
        menu = handler(payload or {})
        if inspect.isawaitable(menu):
            menu = await menu
        if menu is None:
            return None
        if not isinstance(menu, Component) or menu.get("type") != "ContextMenu":
            raise TypeError("on_context_menu must return a ContextMenu component")
        self._transient_handlers.update(collect_handlers(menu))
        return menu.to_json()

    def on_event(self, component_id: str, event: str, handler: Callable) -> Callable:
        """Register an event handler for a renderer root or component id."""
        self._explicit_handlers[(component_id, event)] = handler
        return handler

    def off_event(self, component_id: str, event: str) -> None:
        self._explicit_handlers.pop((component_id, event), None)

    def invoke_component(
        self,
        component_id: str,
        method: str,
        arguments: Optional[dict] = None,
        callback: Optional[Callable] = None,
    ) -> None:
        """Invokes a typed operation on a mounted component in this instance."""
        if self._closed:
            raise ViewProtocolError("view is closed")
        self._bridge.push_wait_response(
            request(
                "sdk.view.component.invoke",
                payload={
                    **self._keys(),
                    "componentId": component_id,
                    "method": method,
                    "arguments": arguments or {},
                },
            ),
            callback=callback,
        )

    @property
    def visible(self) -> bool:
        return self._visible

    def on_visibility(self, handler: Callable[[bool], None]) -> Callable:
        self._visibility_handlers.append(handler)
        return handler

    def visibility_sync(self, visible: bool) -> None:
        if visible == self._visible:
            return
        self._visible = visible
        if visible and self._needs_snapshot:
            self.snapshot(self._nodes, revision=self.revision + 1)
        for handler in list(self._visibility_handlers):
            handler(visible)

    # -- Routing ------------------------------------------------------------

    @property
    def route(self) -> str:
        """The instance's current route, as of the last host sync."""
        return self._route

    @property
    def route_stack(self) -> list[str]:
        return list(self._route_stack)

    @property
    def route_params(self) -> dict:
        return dict(self._route_params)

    def on_route(self, handler: Callable) -> Callable:
        """Registers a handler called with (route, params) on every route sync."""
        self._route_handlers.append(handler)
        return handler

    def push_route(
        self,
        route: str,
        params: Optional[dict] = None,
        callback: Optional[Callable] = None,
    ) -> None:
        self._send_route("sdk.view.route.push", route, params, callback)

    def replace_route(
        self,
        route: str,
        params: Optional[dict] = None,
        callback: Optional[Callable] = None,
    ) -> None:
        self._send_route("sdk.view.route.replace", route, params, callback)

    def goto_route(
        self,
        route: str,
        params: Optional[dict] = None,
        callback: Optional[Callable] = None,
    ) -> None:
        self._send_route("sdk.view.route.goto", route, params, callback)

    def pop_route(self, callback: Optional[Callable] = None) -> None:
        if self._closed:
            raise ViewProtocolError("view is closed")
        self._bridge.push_wait_response(
            request("sdk.view.route.pop", payload=self._keys()), callback=callback
        )

    def _send_route(
        self,
        type: str,
        route: str,
        params: Optional[dict],
        callback: Optional[Callable],
    ) -> None:
        if self._closed:
            raise ViewProtocolError("view is closed")
        payload: dict[str, Any] = {**self._keys(), "route": route}
        if params is not None:
            payload["params"] = params
        self._bridge.push_wait_response(
            request(type, payload=payload), callback=callback
        )

    def route_sync(
        self, route: str, stack: list, params: Optional[dict] = None
    ) -> None:
        """Handles an ``ide.view.route.sync`` control frame."""
        self._route = route
        self._route_stack = [str(entry) for entry in stack] or [route]
        self._route_params = dict(params or {})
        for handler in list(self._route_handlers):
            handler(route, self._route_params)

    # -- Mutations ----------------------------------------------------------

    def insert(self, id: str, data: dict, index: Optional[int] = None) -> None:
        self._queue(PatchOp("insert", id, index=index, data=data))

    def update(self, id: str, data: dict) -> None:
        self._queue(PatchOp("update", id, data=data))

    def remove(self, id: str) -> None:
        self._queue(PatchOp("remove", id))

    def move(self, id: str, index: int) -> None:
        self._queue(PatchOp("move", id, index=index))

    def _queue(self, op: PatchOp) -> None:
        if self._closed:
            raise ViewProtocolError("view is closed")
        if op.op == "insert" and all(
            node.get("id") != op.id for node in self._nodes
        ):
            pending_delta = sum(
                1 if queued.op == "insert" else -1 if queued.op == "remove" else 0
                for queued in self._pending
            )
            if len(self._nodes) + pending_delta >= MAX_SNAPSHOT_NODES:
                raise ViewProtocolError(
                    f"view exceeds {MAX_SNAPSHOT_NODES} nodes"
                )
        if not self._visible:
            if (
                op.op == "insert"
                and len(self._nodes) >= MAX_SNAPSHOT_NODES
                and all(node.get("id") != op.id for node in self._nodes)
            ):
                raise ViewProtocolError(
                    f"view exceeds {MAX_SNAPSHOT_NODES} nodes"
                )
            self._apply_locally([op])
            self._handlers = collect_handlers(self._nodes)
            self._transient_handlers.clear()
            self._needs_snapshot = True
            return
        self._pending.append(op)
        if self._batch_depth == 0:
            self.flush()

    @contextmanager
    def batch(self):
        """Groups operations so they are sent as one patch transaction."""
        self._batch_depth += 1
        try:
            yield self
        finally:
            self._batch_depth -= 1
            if self._batch_depth == 0:
                self.flush()

    def flush(self) -> bool:
        """Sends queued operations as one patch, unless one is already in flight.

        Returns True when a patch was sent. While a patch is in flight the
        operations stay queued and are merged into the next one.
        """
        if self._closed or not self._pending or self._in_flight is not None:
            return False
        ops = self._pending[:MAX_PATCH_OPS]
        payload = {
            **self._keys(),
            "baseRevision": self.revision,
            "revision": self.revision + 1,
            "ops": [op.to_json() for op in ops],
        }
        while (
            len(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
            > MAX_VIEW_PAYLOAD_BYTES
            and len(ops) > 1
        ):
            ops = ops[: max(1, len(ops) // 2)]
            payload["ops"] = [op.to_json() for op in ops]
        if (
            len(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
            > MAX_VIEW_PAYLOAD_BYTES
        ):
            raise ViewProtocolError(
                f"patch operation exceeds {MAX_VIEW_PAYLOAD_BYTES} bytes"
            )
        self._pending = self._pending[len(ops):]
        base = self.revision
        next_revision = base + 1
        self._in_flight = next_revision
        self._apply_locally(ops)
        # Node set changed, so refresh the handler table from the new model.
        self._handlers = collect_handlers(self._nodes)
        self._transient_handlers.clear()
        self._bridge.push_wait_response(
            request(
                "sdk.view.patch",
                payload=payload,
            ),
            callback=self._on_patch_response,
        )
        return True

    def _apply_locally(self, ops: list[PatchOp]) -> None:
        """Mirrors the host's transaction so local state matches after an ack."""
        for op in ops:
            index = next(
                (i for i, n in enumerate(self._nodes) if n.get("id") == op.id), -1
            )
            if op.op == "insert":
                node = {**(op.data or {}), "id": op.id}
                if op.index is None or op.index >= len(self._nodes):
                    self._nodes.append(node)
                else:
                    self._nodes.insert(op.index, node)
            elif op.op == "update" and index != -1:
                self._nodes[index] = {
                    **self._nodes[index],
                    **(op.data or {}),
                    "id": op.id,
                }
            elif op.op == "remove" and index != -1:
                self._nodes.pop(index)
            elif op.op == "move" and index != -1 and op.index is not None:
                node = self._nodes.pop(index)
                self._nodes.insert(op.index, node)

    # -- Host responses -----------------------------------------------------

    def _on_patch_response(self, data=None, error=None, **_):
        if error is not None:
            if getattr(error, "code", None) == "delivery_paused":
                # Keep the locally updated model. The IDE sends an explicit
                # ide.view.resync frame when the user resumes delivery.
                self._in_flight = None
                return
            # The host rejected the patch: re-send a full snapshot so both sides
            # converge, then flush anything queued since.
            self._in_flight = None
            self.resync()
            return
        applied = self._in_flight
        self._in_flight = None
        if applied is not None:
            self.revision = applied
        # Anything queued while this patch was in flight goes out now.
        self.flush()

    def ack(self, revision: int) -> None:
        """Handles an ``ide.view.ack`` control frame."""
        self._in_flight = None
        self.revision = revision
        self.flush()

    def nack(self, reason: Optional[str] = None) -> None:
        """Handles an ``ide.view.nack``: drop the patch and resynchronize."""
        self._in_flight = None
        self.resync()

    def resync(self) -> None:
        """Re-sends the current model as a snapshot (after nack or reconnect)."""
        if self._closed:
            return
        nodes = list(self._nodes)
        self._pending.clear()
        self.snapshot(nodes, revision=self.revision + 1)


class Views:
    """Creates and tracks the plugin's native view models."""

    def __init__(self, bridge: "Bridge"):
        self._bridge = bridge
        self._models: dict[tuple[str, str], ViewModel] = {}

    def create(self, view_id: str, instance_id: Optional[str] = None) -> ViewModel:
        model = ViewModel(self._bridge, view_id, instance_id)
        self._models[(model.view_id, model.instance_id)] = model
        return model

    def outline(
        self,
        view_id: str,
        instance_id: Optional[str] = None,
        *,
        title: str = "Outline",
        actions=(),
    ):
        """Creates a typed ``native.outline`` view facade."""
        from .native_views import OutlineView

        return OutlineView(
            self.create(view_id, instance_id),
            title=title,
            actions=actions,
        )

    def tree(
        self,
        view_id: str,
        instance_id: Optional[str] = None,
        *,
        title: str = "Tree",
        actions=(),
        expanded_ids=None,
        selected_id=None,
        indent=None,
        searchable=None,
        empty_label=None,
    ):
        """Creates a typed ``native.tree`` view facade."""
        from .native_views import TreeView

        view = TreeView(self.create(view_id, instance_id), title=title, actions=actions)
        view.configure(
            expanded_ids=expanded_ids,
            selected_id=selected_id,
            indent=indent,
            searchable=searchable,
            empty_label=empty_label,
        )
        return view

    def virtual_list(
        self,
        view_id: str,
        instance_id: Optional[str] = None,
        *,
        title: str = "List",
        actions=(),
        item_count=None,
        item_height=None,
        selected_id=None,
        empty_label=None,
    ):
        """Creates a typed ``native.virtualList`` view facade."""
        from .native_views import VirtualListView

        view = VirtualListView(
            self.create(view_id, instance_id), title=title, actions=actions
        )
        view.configure(
            item_count=item_count,
            item_height=item_height,
            selected_id=selected_id,
            empty_label=empty_label,
        )
        return view

    def table(
        self,
        view_id: str,
        instance_id: Optional[str] = None,
        *,
        title: str = "Table",
        columns=(),
        actions=(),
        row_count=None,
        row_height=None,
        show_header=None,
        selected_id=None,
        sort_column=None,
        sort_ascending=None,
        empty_label=None,
    ):
        """Creates a typed ``native.table`` view facade."""
        from .native_views import TableView

        view = TableView(
            self.create(view_id, instance_id), title=title, actions=actions
        )
        view.set_columns(columns)
        view.configure(
            row_count=row_count,
            row_height=row_height,
            show_header=show_header,
            selected_id=selected_id,
            sort_column=sort_column,
            sort_ascending=sort_ascending,
            empty_label=empty_label,
        )
        return view

    def form(
        self,
        view_id: str,
        instance_id: Optional[str] = None,
        *,
        title: str = "Form",
        actions=(),
    ):
        """Creates a typed ``native.form`` view facade."""
        from .native_views import FormView

        return FormView(self.create(view_id, instance_id), title=title, actions=actions)

    def markdown(
        self,
        view_id: str,
        instance_id: Optional[str] = None,
        *,
        title: str = "Markdown",
        actions=(),
    ):
        """Creates a typed ``native.markdown`` view facade."""
        from .native_views import MarkdownView

        return MarkdownView(
            self.create(view_id, instance_id), title=title, actions=actions
        )

    def log(
        self,
        view_id: str,
        instance_id: Optional[str] = None,
        *,
        title: str = "Log",
        actions=(),
        item_height=None,
        empty_label=None,
    ):
        """Creates a typed ``native.log`` view facade."""
        from .native_views import LogView

        view = LogView(self.create(view_id, instance_id), title=title, actions=actions)
        view.configure(item_height=item_height, empty_label=empty_label)
        return view

    def variable_inspector(
        self,
        view_id: str,
        instance_id: Optional[str] = None,
        *,
        title: str = "Device Variables",
        actions=(),
    ):
        """Creates a typed ``native.variableInspector`` view facade."""
        from .native_views import VariableInspectorView

        return VariableInspectorView(
            self.create(view_id, instance_id),
            title=title,
            actions=actions,
        )

    def get(
        self, instance_id: str, view_id: Optional[str] = None
    ) -> Optional[ViewModel]:
        if view_id is not None:
            return self._models.get((view_id, instance_id))
        matches = [
            model
            for (
                candidate_view_id,
                candidate_instance_id,
            ), model in self._models.items()
            if candidate_instance_id == instance_id
        ]
        return matches[0] if len(matches) == 1 else None

    def handle_frame(self, type: str, payload: dict) -> None:
        """Routes an inbound ``ide.view.*`` control frame to its model."""
        instance = payload.get("instance") or {}
        instance_id = instance.get("instanceId") or payload.get("instanceId")
        view_id = instance.get("viewId") or payload.get("viewId")
        model = (
            self.get(str(instance_id), str(view_id))
            if view_id
            else self.get(str(instance_id))
        )
        if model is None:
            return
        if type == "ide.view.ack":
            revision = payload.get("revision")
            if isinstance(revision, int):
                model.ack(revision)
        elif type == "ide.view.nack":
            model.nack(payload.get("reason"))
        elif type == "ide.view.resync":
            model.resync()
        elif type == "ide.view.route.sync":
            route = payload.get("route")
            if route:
                model.route_sync(
                    str(route),
                    payload.get("stack") or [],
                    payload.get("params") or {},
                )
        elif type == "ide.view.event":
            component_id = payload.get("componentId")
            event = payload.get("event")
            if component_id and event:
                model.dispatch_event(
                    str(component_id), str(event), payload.get("payload") or {}
                )
        elif type == "ide.view.visibility.changed":
            model.visibility_sync(bool(payload.get("visible", False)))

    async def handle_context_menu_request(self, payload: dict) -> Optional[dict]:
        instance = payload.get("instance") or {}
        instance_id = instance.get("instanceId") or payload.get("instanceId")
        view_id = instance.get("viewId") or payload.get("viewId")
        component_id = payload.get("componentId")
        if not instance_id or not component_id:
            return None
        model = (
            self.get(str(instance_id), str(view_id))
            if view_id
            else self.get(str(instance_id))
        )
        if model is None:
            return None
        return await model.request_context_menu(str(component_id), payload)

    def resync_all(self) -> None:
        """Re-sends snapshots for every open view (used after a reconnect)."""
        for model in self._models.values():
            model.resync()

    def dispose_all(self) -> None:
        self._models.clear()
