from __future__ import annotations

import inspect
import json
from contextlib import contextmanager
from typing import (
    Any,
    Callable,
    Iterable,
    Iterator,
    Literal,
    Optional,
    TYPE_CHECKING,
)
from uuid import uuid4

from ..models.schema import request
from .components import (
    AUTO_ID_PREFIX,
    Component,
    _bind_component_value,
    _wire_component_value,
    collect_handlers,
)

if TYPE_CHECKING:
    from ..core.bridge import Bridge
    from .native_views import (
        FormView,
        LogView,
        MarkdownView,
        OutlineView,
        TableColumn,
        TableView,
        TreeView,
        VariableInspectorView,
        ViewAction,
        VirtualListView,
    )


MAX_SNAPSHOT_NODES = 20_000
MAX_PATCH_OPS = 2_000
MAX_VIEW_PAYLOAD_BYTES = 2 * 1024 * 1024


class ViewProtocolError(Exception):
    """Raised when a view operation is invalid before it reaches the host."""


# -- Component tree normalization -------------------------------------------
#
# A component view is a single wrapper node:
#
#     {"id": "root", "component": {"type": "Column", "props": {"id": "root"}, ...}}
#
# The host addresses patches by a node's top-level ``id``. Components carry
# their identity in ``props.id``, so a bare component root can never be patched
# by id. ``_normalize_model`` wraps bare component roots and gives every
# auto-generated component id a deterministic structural value. Rebuilding the
# same tree therefore produces the same ids, and the host keeps the widget state
# (text controllers, expansion, selection) keyed by those ids.
_COMPONENT_KEYS = frozenset({"type", "props", "children", "events"})


def _is_auto_id(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(AUTO_ID_PREFIX)


def _component_props_id(node: Any) -> Optional[str]:
    if not isinstance(node, dict):
        return None
    props = node.get("props")
    if isinstance(props, dict):
        candidate = props.get("id")
        if isinstance(candidate, str) and candidate:
            return candidate
    return None


def _is_wrapper(node: Any) -> bool:
    return isinstance(node, dict) and isinstance(node.get("component"), dict)


def _looks_like_component(node: Any) -> bool:
    """True for a bare ``{type, props, children, events}`` schema node."""
    if isinstance(node, Component):
        return True
    if not isinstance(node, dict) or _is_wrapper(node):
        return False
    if not isinstance(node.get("type"), str) or not node["type"]:
        return False
    if not set(node).issubset(_COMPONENT_KEYS):
        return False
    return (
        isinstance(node.get("props"), dict)
        or "children" in node
        or "events" in node
    )


def _stable_auto_id(path: str) -> str:
    return AUTO_ID_PREFIX + path


def _stabilize_component(
    node: dict[str, Any],
    path: str,
    forced_id: Optional[str] = None,
) -> str:
    """Rewrites auto ids in one component subtree; returns its root id."""
    props = node.get("props")
    if not isinstance(props, dict):
        props = {}
        node["props"] = props
    current = props.get("id")
    if forced_id is not None:
        props["id"] = forced_id
    elif not isinstance(current, str) or not current or _is_auto_id(current):
        props["id"] = _stable_auto_id(path)
    for key, child in list(props.items()):
        if key != "id":
            _stabilize_value(child, f"{path}/props/{key}")
    children = node.get("children")
    if isinstance(children, list):
        for index, child in enumerate(children):
            _stabilize_value(child, f"{path}/children/{index}")
    return str(props["id"])


def _stabilize_value(value: Any, path: str) -> None:
    """Rewrites builder-generated ids to deterministic structural ids."""
    if isinstance(value, Component):
        _stabilize_component(value, path)
    elif isinstance(value, dict):
        if _is_wrapper(value):
            component = value["component"]
            top = value.get("id")
            if isinstance(top, str) and top and not _is_auto_id(top):
                _stabilize_component(component, f"{path}/component")
            else:
                value["id"] = _stabilize_component(
                    component, f"{path}/component"
                )
            for key, child in list(value.items()):
                if key not in ("id", "component"):
                    _stabilize_value(child, f"{path}/{key}")
        elif _looks_like_component(value):
            _stabilize_component(value, path)
        else:
            if _is_auto_id(value.get("id")):
                value["id"] = _stable_auto_id(path)
            for key, child in list(value.items()):
                if key != "id":
                    _stabilize_value(child, f"{path}/{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _stabilize_value(child, f"{path}/{index}")


def _normalize_model(nodes: list[Any]) -> list[Any]:
    """Returns the model in wire shape, wrapping a single component root.

    Raises ``ViewProtocolError`` when component roots are mixed with data
    nodes: that shape is ambiguous and the host would silently fall back to a
    renderer that cannot display a component tree.
    """
    if not nodes:
        return []
    component_roots = [
        node
        for node in nodes
        if isinstance(node, Component)
        or _is_wrapper(node)
        or _looks_like_component(node)
    ]
    if not component_roots:
        normalized = list(nodes)
        for index, node in enumerate(normalized):
            _stabilize_value(node, f"r{index}")
        return normalized

    if len(nodes) != 1:
        raise ViewProtocolError(
            "component views require exactly one root component; "
            f"got {len(nodes)} nodes"
        )
    root = component_roots[0]
    if _is_wrapper(root):
        _stabilize_value(root, "r0")
        return [root]

    # Wrap the bare root first so a snapshot and every later patch stabilize
    # ids with the same path ("r0/component").
    explicit = _component_props_id(root)
    if explicit is not None and _is_auto_id(explicit):
        explicit = None
    root_id = _stabilize_component(root, "r0/component", forced_id=explicit)
    wrapper = {"id": root_id, "component": root}
    _stabilize_value(wrapper, "r0")
    return [wrapper]


def _looks_like_partial_props(data: Any) -> bool:
    return (
        isinstance(data, dict)
        and set(data) == {"props"}
        and isinstance(data.get("props"), dict)
    )


def _with_merged_props(node: dict[str, Any], extra: dict[str, Any]) -> Any:
    props = node.get("props")
    merged = {
        **(props if isinstance(props, dict) else {}),
        **extra,
    }
    if isinstance(node, Component):
        return Component(
            str(node.get("type", "")),
            merged,
            node.get("children"),
            node.get("events"),
        )
    return {**node, "props": merged}


def _find_node(
    nodes: list[Any], target: str
) -> tuple[int, str]:
    """Finds a node by its top-level id or a wrapped component's props.id.

    Returns ``(index, address)`` where ``address`` is the id to put in the
    patch op (the wrapper's top-level id when the target is a nested component).
    """
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        top = node.get("id")
        if isinstance(top, str) and top == target:
            return index, target
        if _is_wrapper(node):
            inner_id = _component_props_id(node.get("component"))
            if inner_id == target and isinstance(top, str) and top:
                return index, top
        elif _component_props_id(node) == target:
            return index, top if isinstance(top, str) and top else target
    return -1, target


class PatchOp:
    """One operation in a patch transaction."""

    __slots__ = ("op", "id", "index", "data")

    def __init__(
        self,
        op: str,
        id: str,
        index: Optional[int] = None,
        data: Optional[dict[str, Any]] = None,
    ) -> None:
        self.op = op
        self.id = id
        self.index = index
        self.data = data

    def to_json(self) -> dict[str, Any]:
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
    ) -> None:
        self._bridge = bridge
        self.view_id = view_id
        self.instance_id = instance_id or uuid4().hex
        self.revision = 0
        self._nodes: list[dict[str, Any]] = []
        self._pending: list[PatchOp] = []
        self._in_flight: Optional[int] = None
        self._closed = False
        self._batch_depth = 0
        # Routing is per view instance: the host owns the authoritative stack and
        # pushes it back on ide.view.route.sync, so these mirror the last sync.
        self._route = "home"
        self._route_stack: list[str] = ["home"]
        self._route_params: dict[str, Any] = {}
        self._route_handlers: list[
            Callable[[str, dict[str, Any]], None]
        ] = []
        # (component_id, event) -> handler, rebuilt from the component tree on
        # every snapshot/patch so a removed component's handler goes with it.
        self._handlers: dict[tuple[str, str], Callable[..., Any]] = {}
        self._transient_handlers: dict[
            tuple[str, str], Callable[..., Any]
        ] = {}
        # Renderer-driven views send plain data nodes rather than a component
        # tree. Their root events are registered explicitly and survive model
        # snapshots, unlike handlers collected from component nodes.
        self._explicit_handlers: dict[
            tuple[str, str], Callable[..., Any]
        ] = {}
        self._visible = True
        self._needs_snapshot = False
        self._visibility_handlers: list[Callable[[bool], None]] = []
        self._sync_error_handlers: list[Callable[[ViewProtocolError], None]] = []
        #: Last error that made the SDK fall back to a full snapshot, or that a
        #: stale/invalid local operation was dropped for. Plugins can poll this
        #: or subscribe with :meth:`on_sync_error`.
        self.last_sync_error: Optional[ViewProtocolError] = None

    # -- Identity -----------------------------------------------------------

    def _keys(self) -> dict[str, str]:
        return {"viewId": self.view_id, "instanceId": self.instance_id}

    @property
    def nodes(self) -> list[dict[str, Any]]:
        return list(self._nodes)

    @property
    def has_in_flight(self) -> bool:
        return self._in_flight is not None

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    @property
    def needs_snapshot(self) -> bool:
        """True when a snapshot was dropped or rejected and must be resent."""
        return self._needs_snapshot

    # -- Lifecycle ----------------------------------------------------------

    def open(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._bridge.push_wait_response(
            request("sdk.view.open", payload=self._keys()), callback=callback
        )
        # A snapshot taken before the bridge loop was live (e.g. in __init__)
        # was dropped by push. open() runs from on_start with the handshake
        # complete, so resend the current model now. Resend even when the
        # snapshot was delivered previously: the host's open handler installs
        # an empty loading model, and skipping the snapshot would leave the
        # view blank forever after a second open.
        if self._nodes and not self._closed:
            self.snapshot(
                self._pending_applied_nodes(), revision=self.revision + 1
            )

    def close(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._closed = True
        self._pending.clear()
        self._in_flight = None
        self._bridge.push_wait_response(
            request("sdk.view.close", payload=self._keys()), callback=callback
        )

    def snapshot(
        self,
        nodes: list[dict[str, Any]],
        revision: Optional[int] = None,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        """Sends a full snapshot and resets local patch state.

        A single bare ``Component`` root (or a single component-schema dict) is
        normalized to the wrapper shape ``{"id": ..., "component": {...}}`` so
        later patches can address it by top-level id. Component views may only
        have one root; mixing component roots with data nodes raises
        :class:`ViewProtocolError`.
        """
        if self._closed:
            raise ViewProtocolError("view is closed")
        if len(nodes) > MAX_SNAPSHOT_NODES:
            raise ViewProtocolError(
                f"snapshot exceeds {MAX_SNAPSHOT_NODES} nodes"
            )
        # Normalize (and validate) before touching the committed model, so a
        # rejected snapshot leaves _nodes/revision/_pending unchanged.
        prepared = _normalize_model(list(nodes))
        payload = {
            **self._keys(),
            "revision": 1 if revision is None else revision,
            "nodes": [self._wire_node(node) for node in prepared],
        }
        if (
            len(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
            > MAX_VIEW_PAYLOAD_BYTES
        ):
            raise ViewProtocolError(
                f"snapshot exceeds {MAX_VIEW_PAYLOAD_BYTES} bytes"
            )

        # Component instances are preserved (not copied into plain dicts) so
        # later patches can rebind and collect their handlers.
        self._nodes = prepared
        for node in self._nodes:
            _bind_component_value(node, self)
        self.revision = payload["revision"]
        self._pending.clear()
        self._in_flight = None
        # Rebuild the handler table from this snapshot, so handlers for nodes
        # that are gone do not linger.
        self._handlers = collect_handlers(self._nodes)
        self._transient_handlers.clear()
        # push returns False when the bridge loop is not live yet (e.g. a
        # snapshot sent from __init__, before plugin.start()). In that case the
        # frame was dropped, so keep _needs_snapshot set: open() resends it once
        # the handshake has completed. A host error response also marks the
        # snapshot unsent, so the next open/visibility change retries it.
        delivered = self._bridge.push_wait_response(
            request(
                "sdk.view.snapshot",
                payload=payload,
            ),
            callback=self._snapshot_callback(callback),
        )
        self._needs_snapshot = not delivered

    @staticmethod
    def _wire_node(node: Any) -> Any:
        """One node in wire form, with component handlers reduced to markers."""
        return _wire_component_value(node)

    def _wire_nodes(self) -> list[Any]:
        """Nodes in wire form, with component handlers reduced to markers."""
        return [self._wire_node(node) for node in self._nodes]

    def _snapshot_callback(
        self, callback: Optional[Callable[..., Any]]
    ) -> Callable[..., Any]:
        def _done(data: Any = None, error: Any = None, **kwargs: Any) -> None:
            if error is not None and getattr(error, "code", None) != (
                "delivery_paused"
            ):
                self._needs_snapshot = True
                self._report_sync_error(
                    error
                    if isinstance(error, ViewProtocolError)
                    else ViewProtocolError(str(error))
                )
            if callback is not None:
                callback(data=data, error=error, **kwargs)

        return _done

    def dispatch_event(
        self,
        component_id: str,
        event: str,
        payload: Optional[dict[str, Any]] = None,
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
        self,
        component_id: str,
        payload: Optional[dict[str, Any]] = None,
    ) -> Optional[dict[str, Any]]:
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

    def on_event(
        self,
        component_id: str,
        event: str,
        handler: Callable[..., Any],
    ) -> Callable[..., Any]:
        """Register an event handler for a renderer root or component id."""
        self._explicit_handlers[(component_id, event)] = handler
        return handler

    def off_event(self, component_id: str, event: str) -> None:
        self._explicit_handlers.pop((component_id, event), None)

    def invoke_component(
        self,
        component_id: str,
        method: str,
        arguments: Optional[dict[str, Any]] = None,
        callback: Optional[Callable[..., Any]] = None,
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

    def on_visibility(
        self, handler: Callable[[bool], None]
    ) -> Callable[[bool], None]:
        self._visibility_handlers.append(handler)
        return handler

    def visibility_sync(self, visible: bool) -> None:
        if visible == self._visible:
            return
        self._visible = visible
        if visible and self._needs_snapshot:
            self.snapshot(
                self._pending_applied_nodes(), revision=self.revision + 1
            )
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
    def route_params(self) -> dict[str, Any]:
        return dict(self._route_params)

    def on_route(
        self, handler: Callable[[str, dict[str, Any]], None]
    ) -> Callable[[str, dict[str, Any]], None]:
        """Registers a handler called with (route, params) on every route sync."""
        self._route_handlers.append(handler)
        return handler

    def push_route(
        self,
        route: str,
        params: Optional[dict[str, Any]] = None,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._send_route("sdk.view.route.push", route, params, callback)

    def replace_route(
        self,
        route: str,
        params: Optional[dict[str, Any]] = None,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._send_route("sdk.view.route.replace", route, params, callback)

    def goto_route(
        self,
        route: str,
        params: Optional[dict[str, Any]] = None,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._send_route("sdk.view.route.goto", route, params, callback)

    def pop_route(self, callback: Optional[Callable[..., Any]] = None) -> None:
        if self._closed:
            raise ViewProtocolError("view is closed")
        self._bridge.push_wait_response(
            request("sdk.view.route.pop", payload=self._keys()), callback=callback
        )

    def _send_route(
        self,
        type: str,
        route: str,
        params: Optional[dict[str, Any]],
        callback: Optional[Callable[..., Any]],
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
        self,
        route: str,
        stack: list[Any],
        params: Optional[dict[str, Any]] = None,
    ) -> None:
        """Handles an ``ide.view.route.sync`` control frame."""
        self._route = route
        self._route_stack = [str(entry) for entry in stack] or [route]
        self._route_params = dict(params or {})
        for handler in list(self._route_handlers):
            handler(route, self._route_params)

    # -- Mutations ----------------------------------------------------------

    @property
    def component_root_id(self) -> Optional[str]:
        """The wrapper id of this view's component root, if it has one."""
        for node in self._nodes:
            if _is_wrapper(node):
                top = node.get("id")
                if isinstance(top, str) and top:
                    return top
        return None

    def set_content(
        self,
        component: Component,
        revision: Optional[int] = None,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        """Replaces the whole component tree with [component]."""
        self.snapshot([component], revision=revision, callback=callback)

    def update_root(self, component: Component) -> None:
        """Replaces the wrapped root component without rebuilding the view."""
        root_id = self.component_root_id
        if root_id is None:
            raise ViewProtocolError(
                "view has no component root; call snapshot/set_content first"
            )
        self.update(root_id, component)

    def insert(
        self, id: str, data: dict[str, Any], index: Optional[int] = None
    ) -> None:
        self._queue(PatchOp("insert", id, index=index, data=data))

    def update(self, id: str, data: dict[str, Any]) -> None:
        """Replaces the node addressed by [id].

        For a component view, [data] may be a ``Component`` (or a component
        schema dict), which replaces the wrapped root's component while keeping
        the same top-level id. ``{"props": {...}}`` merges into the component's
        props instead of replacing the whole tree, so a partial update cannot
        drop ``props.id``, children, or event markers.
        """
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
            _, working = self._apply_transaction([op], self._nodes)
            self._nodes = working
            for node in self._nodes:
                _bind_component_value(node, self)
            self._handlers = collect_handlers(self._nodes)
            self._transient_handlers.clear()
            self._needs_snapshot = True
            return
        self._pending.append(op)
        if self._batch_depth == 0:
            self.flush()

    @contextmanager
    def batch(self) -> Iterator["ViewModel"]:
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
        operations stay queued and are merged into the next one. When the
        bridge is not live the operations stay queued instead of leaving an
        ``_in_flight`` revision that can never receive a response.
        """
        if self._closed or not self._pending or self._in_flight is not None:
            return False
        sent_revision = self.revision + 1
        candidates = self._pending[:MAX_PATCH_OPS]
        while True:
            # Apply on a working copy first: an op that the host would reject
            # must raise before anything is sent or committed locally.
            prepared, working = self._apply_transaction(
                candidates, self._nodes
            )
            payload = {
                **self._keys(),
                "baseRevision": self.revision,
                "revision": sent_revision,
                "ops": [op.to_json() for op in prepared],
            }
            encoded = len(
                json.dumps(payload, separators=(",", ":")).encode("utf-8")
            )
            if encoded <= MAX_VIEW_PAYLOAD_BYTES:
                break
            if len(candidates) == 1:
                raise ViewProtocolError(
                    f"patch operation exceeds {MAX_VIEW_PAYLOAD_BYTES} bytes"
                )
            candidates = candidates[: max(1, len(candidates) // 2)]

        # Bind the response to the revision that was actually sent. The host
        # sends ide.view.ack before the request response, and ack() flushes a
        # newer patch immediately, so by the time this response arrives
        # _in_flight may already refer to the next patch. Without the binding
        # the stale response would release and acknowledge that newer patch.
        pushed = self._bridge.push_wait_response(
            request(
                "sdk.view.patch",
                payload=payload,
            ),
            callback=lambda data=None, error=None, **_: self._on_patch_response(
                data, error, sent_revision=sent_revision
            ),
        )
        if not pushed:
            # Nothing was delivered. Keep the pending ops for the next attempt;
            # in particular do not set _in_flight, or every later flush would
            # short-circuit forever.
            return False

        self._nodes = working
        for node in self._nodes:
            _bind_component_value(node, self)
        # Node set changed, so refresh the handler table from the new model.
        self._handlers = collect_handlers(self._nodes)
        self._transient_handlers.clear()
        self._pending = self._pending[len(candidates):]
        self._in_flight = sent_revision
        return True

    def _prepare_insert_data(self, data: Any, op_id: str) -> dict[str, Any]:
        """Normalizes insert data so component roots arrive in wrapper shape."""
        if isinstance(data, Component):
            props = data.get("props")
            if not isinstance(props, dict):
                props = {}
                data["props"] = props
            if not props.get("id") or _is_auto_id(props.get("id")):
                props["id"] = op_id
            return {"component": data}
        if isinstance(data, dict):
            if _is_wrapper(data) or not _looks_like_component(data):
                return data
            props = data.get("props")
            if not isinstance(props, dict):
                props = {}
                data["props"] = props
            if not props.get("id") or _is_auto_id(props.get("id")):
                props["id"] = op_id
            return {"component": data}
        return data

    def _prepare_update_data(
        self, old: dict[str, Any], data: Any
    ) -> dict[str, Any]:
        """Normalizes update data against the node it replaces."""
        if _is_wrapper(old):
            if isinstance(data, Component):
                return {"component": data}
            if isinstance(data, dict):
                if _is_wrapper(data):
                    return data
                if _looks_like_component(data):
                    return {"component": data}
                inner = old.get("component")
                if _looks_like_partial_props(data) and isinstance(
                    inner, dict
                ):
                    return {
                        "component": _with_merged_props(
                            inner, data["props"]
                        )
                    }
            return data
        if (
            isinstance(data, dict)
            and isinstance(data.get("props"), dict)
            and isinstance(old.get("props"), dict)
        ):
            # A partial props update must not drop id/children/events.
            return {
                **data,
                "props": {**old["props"], **data["props"]},
            }
        return data

    def _apply_transaction(
        self, ops: list[PatchOp], nodes: list[Any]
    ) -> tuple[list[PatchOp], list[Any]]:
        """Validates and applies [ops] to a working copy.

        The committed ``_nodes`` is untouched on failure. Returns the ops in
        their wire form (ids resolved to wrapper ids, component data wrapped)
        and the new node list.
        """
        # Pass 1: validate every op against a shadow id list before mutating
        # anything. A later bad op therefore cannot leave earlier ops applied.
        shadow: list[Any] = list(nodes)
        for op in ops:
            if op.op not in ("insert", "update", "remove", "move"):
                raise ViewProtocolError(f"unknown patch op {op.op!r}")
            if op.op == "insert":
                if op.data is None:
                    raise ViewProtocolError(
                        f"insert {op.id} missing data"
                    )
                if _find_node(shadow, op.id)[0] != -1:
                    raise ViewProtocolError(
                        f"insert of existing id {op.id}"
                    )
                if op.index is not None and op.index < 0:
                    raise ViewProtocolError(
                        f"insert {op.id} negative index"
                    )
                # Mirror the wire shape pass 2 builds, including the component
                # wrapper and the insert-address id rewrite, so later ops in
                # this batch resolve the same ids the host will see.
                data = self._prepare_insert_data(op.data, op.id)
                node = {**data, "id": op.id}
                if op.index is None or op.index >= len(shadow):
                    shadow.append(node)
                else:
                    shadow.insert(op.index, node)
                continue
            index, address = _find_node(shadow, op.id)
            if index == -1:
                raise ViewProtocolError(f"{op.op} of missing id {op.id}")
            if op.op == "update":
                if op.data is None:
                    raise ViewProtocolError(f"update {op.id} missing data")
                # Apply the update to the shadow exactly as pass 2 will apply
                # it. Otherwise a later op that still addresses the old
                # component id would validate here but fail (or, worse, hit
                # the wrong node) once the id has actually changed.
                old = shadow[index]
                data = self._prepare_update_data(old, op.data)
                shadow[index] = {**old, **data, "id": address}
                continue
            if op.op == "move":
                if (
                    op.index is None
                    or op.index < 0
                    or op.index >= len(shadow)
                ):
                    raise ViewProtocolError(
                        f"move {op.id} index out of range"
                    )
                shadow.pop(index)
                shadow.insert(op.index, {"id": op.id})
            elif op.op == "remove":
                shadow.pop(index)

        # Pass 2: apply for real. Validation above guarantees no surprises.
        working: list[Any] = list(nodes)
        prepared: list[PatchOp] = []
        for op in ops:
            index, address = _find_node(working, op.id)
            if op.op != "insert" and index == -1:
                # Pass 1 mirrors every transformation, so this would mean the
                # shadow and the working copy diverged. Never fall through to
                # working[-1], which would silently modify the last node.
                raise ViewProtocolError(f"{op.op} of missing id {op.id}")
            if op.op == "insert":
                data = self._prepare_insert_data(op.data, op.id)
                node = {**data, "id": op.id}
                if op.index is None or op.index >= len(working):
                    working.append(node)
                else:
                    working.insert(op.index, node)
                prepared.append(
                    PatchOp("insert", address, index=op.index, data=data)
                )
            elif op.op == "update":
                old = working[index]
                data = self._prepare_update_data(old, op.data)
                working[index] = {**old, **data, "id": address}
                prepared.append(PatchOp("update", address, data=data))
            elif op.op == "remove":
                working.pop(index)
                prepared.append(PatchOp("remove", address))
            else:
                node = working.pop(index)
                working.insert(op.index, node)
                prepared.append(
                    PatchOp("move", address, index=op.index)
                )

        # Re-run structural id stabilization over the whole model so a rebuild
        # and an incremental update produce identical auto ids.
        for index, node in enumerate(working):
            _stabilize_value(node, f"r{index}")
        return prepared, working

    def _pending_applied_nodes(self) -> list[Any]:
        """Applies queued ops locally before a resync/snapshot.

        Pending ops used to be dropped when a patch was rejected, so updates
        queued while another patch was in flight vanished. They are applied to
        the local model instead and travel in the replacement snapshot.
        """
        if not self._pending:
            return list(self._nodes)
        try:
            _, nodes = self._apply_transaction(
                list(self._pending), self._nodes
            )
        except ViewProtocolError as error:
            # An invalid queued op cannot be expressed in a snapshot. Surface
            # it instead of silently discarding the rest of the batch.
            self._report_sync_error(error)
            nodes = list(self._nodes)
        self._pending.clear()
        return nodes

    def _report_sync_error(self, error: ViewProtocolError) -> None:
        self.last_sync_error = error
        for handler in list(self._sync_error_handlers):
            try:
                handler(error)
            except Exception:
                # A broken listener must not stop the view from recovering.
                continue

    def on_sync_error(
        self, handler: Callable[[ViewProtocolError], None]
    ) -> Callable[[ViewProtocolError], None]:
        """Registers a callback for local-apply/resync failures."""
        self._sync_error_handlers.append(handler)
        return handler

    # -- Host responses -----------------------------------------------------

    def _on_patch_response(
        self,
        data: Any = None,
        error: Any = None,
        *,
        sent_revision: Optional[int] = None,
        **_: Any,
    ) -> None:
        # The response may arrive after an ack/nack for the same revision
        # already released _in_flight (and a newer patch took its place).
        # Responses are only authoritative for the revision that was sent;
        # acting on a stale one would acknowledge the newer patch early.
        if sent_revision is not None and self._in_flight != sent_revision:
            return
        if error is not None:
            if getattr(error, "code", None) == "delivery_paused":
                # Keep the locally updated model. The IDE sends an explicit
                # ide.view.resync frame when the user resumes delivery.
                self._in_flight = None
                return
            if self._in_flight is None:
                # A duplicate/late rejection: nack (or another error response)
                # already triggered resync. Do not send a second snapshot.
                return
            # The host rejected the patch: re-send a full snapshot (including
            # updates queued while this patch was in flight) so both sides
            # converge.
            self._in_flight = None
            self.resync()
            return
        applied = self._in_flight
        self._in_flight = None
        if applied is not None and applied > self.revision:
            self.revision = applied
        # Anything queued while this patch was in flight goes out now.
        self.flush()

    def ack(self, revision: int) -> None:
        """Handles an ``ide.view.ack`` control frame.

        Duplicate/stale acks are ignored: advancing the revision again would
        make the next patch build on a revision the host did not accept.
        """
        if self._closed or revision <= self.revision:
            return
        if self._in_flight is not None and revision < self._in_flight:
            return
        self._in_flight = None
        self.revision = revision
        self.flush()

    def nack(self, reason: Optional[str] = None) -> None:
        """Handles an ``ide.view.nack``: drop the patch and resynchronize."""
        if self._closed or self._in_flight is None:
            return
        self._in_flight = None
        self.resync()

    def resync(self) -> None:
        """Re-sends the current model as a snapshot (after nack or reconnect).

        Updates queued while a patch was in flight are applied locally first,
        so a rejected patch no longer discards them.
        """
        if self._closed:
            return
        nodes = self._pending_applied_nodes()
        self.snapshot(nodes, revision=self.revision + 1)


ViewPlacement = Literal["sidebar", "editor", "expansion"]


class ViewInstance(ViewModel):
    """A plugin view model together with its host placement.

    ``ViewModel`` remains the transport implementation.  Plugin code should
    work with ``ViewInstance`` so that placement and lifecycle are represented
    by the same object as the rendered view.
    """

    def __init__(
        self,
        bridge: "Bridge",
        view_id: str,
        instance_id: Optional[str] = None,
        *,
        placement: ViewPlacement = "sidebar",
        tab_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        super().__init__(bridge, view_id, instance_id)
        self.placement = placement
        self.tab_id = tab_id
        self.session_id = session_id

    @classmethod
    def from_host_response(
        cls,
        bridge: "Bridge",
        data: dict[str, Any],
        *,
        placement: ViewPlacement,
    ) -> "ViewInstance":
        return cls(
            bridge,
            str(data.get("viewId", "")),
            str(data.get("instanceId", "")),
            placement=placement,
            tab_id=data.get("tabId"),
            session_id=data.get("sessionId"),
        )

    def focus(self, callback: Optional[Callable[..., Any]] = None) -> None:
        """Activates this view instance in the host shell."""
        if self.tab_id:
            self._bridge.push_wait_response(
                request("sdk.tab.activate", payload={"tab_id": self.tab_id}),
                callback=callback,
            )
            return
        self._bridge.push_wait_response(
            request("sdk.view.focus", payload=self._keys()),
            callback=callback,
        )

    def close(self, callback: Optional[Callable[..., Any]] = None) -> None:
        """Closes the view instance and its editor tab, when one exists."""
        if not self.tab_id:
            super().close(callback=callback)
            return
        self._closed = True
        self._pending.clear()
        self._in_flight = None
        self._bridge.push_wait_response(
            request("sdk.tab.close", payload={"tab_id": self.tab_id}),
            callback=callback,
        )


class Views:
    """Creates and tracks the plugin's native view instances."""

    def __init__(self, bridge: "Bridge") -> None:
        self._bridge = bridge
        self._models: dict[tuple[str, str], ViewInstance] = {}
        # view_id -> container id, read lazily from the plugin manifest so the
        # default instance id can match the host's sidebar placement.
        self._view_containers: Optional[dict[str, str]] = None

    def create(
        self,
        view_id: str,
        instance_id: Optional[str] = None,
        *,
        placement: ViewPlacement = "sidebar",
        tab_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> ViewInstance:
        # The sidebar host mounts each contributed view at the fixed instance id
        # "container:<containerId>". A plugin that just calls create(view_id) must
        # land on that same key or its snapshot goes to an instance nobody renders
        # (the view spins forever). Default to it from the manifest; an explicit
        # instance_id (e.g. a host-allocated "tab:<n>") still wins.
        if instance_id is None:
            container = self._container_for(view_id)
            if container:
                instance_id = f"container:{container}"
        if placement == "sidebar" and instance_id and instance_id.startswith("tab:"):
            placement = "editor"
        model = ViewInstance(
            self._bridge,
            view_id,
            instance_id,
            placement=placement,
            tab_id=tab_id,
            session_id=session_id,
        )
        self._models[(model.view_id, model.instance_id)] = model
        return model

    def open(
        self,
        view_id: str,
        *,
        placement: ViewPlacement = "sidebar",
        title: Optional[str] = None,
        callback: Optional[Callable[..., Any]] = None,
    ) -> Optional[ViewInstance]:
        """Opens a contributed view in a host placement.

        Sidebar views have a deterministic instance id and are returned
        immediately. Editor and expansion placements require a host-allocated
        instance id, so the resulting ``ViewInstance`` is delivered through
        ``callback(instance=..., error=...)``.
        """
        if placement not in ("sidebar", "editor", "expansion"):
            raise ValueError(f"Unsupported view placement: {placement}")

        if placement == "sidebar":
            instance = self.create(view_id, placement=placement)

            def _opened(data: Any = None, error: Any = None, **_: Any) -> None:
                if callback is None:
                    return
                if error is not None:
                    callback(error=error)
                    return
                callback(instance=instance)

            instance.open(callback=_opened)
            return instance

        payload: dict[str, Any] = {
            "viewId": view_id,
            "expansion": placement == "expansion",
        }
        if title is not None:
            payload["title"] = title

        def _created(data: Any = None, error: Any = None, **_: Any) -> None:
            if error is not None:
                if callback is not None:
                    callback(error=error)
                return
            if not isinstance(data, dict):
                if callback is not None:
                    callback(error=ValueError("Invalid view instance response"))
                return
            instance = ViewInstance.from_host_response(
                self._bridge,
                data,
                placement=placement,
            )
            if not instance.view_id or not instance.instance_id:
                if callback is not None:
                    callback(error=ValueError("View response is missing identity"))
                return
            self._models[(instance.view_id, instance.instance_id)] = instance

            def _opened(data: Any = None, error: Any = None, **_: Any) -> None:
                if callback is None:
                    return
                if error is not None:
                    callback(error=error)
                    return
                callback(instance=instance)

            instance.open(callback=_opened)

        self._bridge.push_wait_response(
            request("sdk.tab.create_view", payload=payload),
            callback=_created,
        )
        return None

    def _container_for(self, view_id: str) -> Optional[str]:
        if self._view_containers is None:
            self._view_containers = self._load_view_containers()
        return self._view_containers.get(view_id)

    @staticmethod
    def _load_view_containers() -> dict[str, str]:
        """Maps each contributed view id to its container id from plugin.toml.

        Best-effort: any failure (standalone run, missing/oddly-shaped manifest)
        yields an empty map, so create() falls back to a random instance id.
        """
        import os
        import tomllib
        from pathlib import Path

        plugin_dir = os.environ.get("PYRITE_IDE_PLUGIN_DIR")
        if not plugin_dir:
            return {}
        manifest_path = Path(plugin_dir) / "plugin.toml"
        try:
            raw = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError, ValueError):
            return {}
        contributes = raw.get("contributes")
        views = contributes.get("views") if isinstance(contributes, dict) else None
        if not isinstance(views, list):
            return {}
        mapping: dict[str, str] = {}
        for view in views:
            if not isinstance(view, dict):
                continue
            view_id = view.get("id")
            container = view.get("container")
            if isinstance(view_id, str) and isinstance(container, str):
                mapping[view_id] = container
        return mapping

    def outline(
        self,
        view_id: str,
        instance_id: Optional[str] = None,
        *,
        title: str = "Outline",
        actions: Iterable["ViewAction"] = (),
    ) -> "OutlineView":
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
        actions: Iterable["ViewAction"] = (),
        expanded_ids: Optional[Iterable[str]] = None,
        selected_id: Optional[str] = None,
        indent: Optional[float] = None,
        searchable: Optional[bool] = None,
        empty_label: Optional[str] = None,
    ) -> "TreeView":
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
        actions: Iterable["ViewAction"] = (),
        item_count: Optional[int] = None,
        item_height: Optional[float] = None,
        selected_id: Optional[str] = None,
        empty_label: Optional[str] = None,
    ) -> "VirtualListView":
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
        columns: Iterable["TableColumn"] = (),
        actions: Iterable["ViewAction"] = (),
        row_count: Optional[int] = None,
        row_height: Optional[float] = None,
        show_header: Optional[bool] = None,
        selected_id: Optional[str] = None,
        sort_column: Optional[str] = None,
        sort_ascending: Optional[bool] = None,
        empty_label: Optional[str] = None,
    ) -> "TableView":
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
        actions: Iterable["ViewAction"] = (),
    ) -> "FormView":
        """Creates a typed ``native.form`` view facade."""
        from .native_views import FormView

        return FormView(self.create(view_id, instance_id), title=title, actions=actions)

    def markdown(
        self,
        view_id: str,
        instance_id: Optional[str] = None,
        *,
        title: str = "Markdown",
        actions: Iterable["ViewAction"] = (),
    ) -> "MarkdownView":
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
        actions: Iterable["ViewAction"] = (),
        item_height: Optional[float] = None,
        empty_label: Optional[str] = None,
    ) -> "LogView":
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
        actions: Iterable["ViewAction"] = (),
    ) -> "VariableInspectorView":
        """Creates a typed ``native.variableInspector`` view facade."""
        from .native_views import VariableInspectorView

        return VariableInspectorView(
            self.create(view_id, instance_id),
            title=title,
            actions=actions,
        )

    def get(
        self, instance_id: str, view_id: Optional[str] = None
    ) -> Optional[ViewInstance]:
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

    def handle_frame(self, type: str, payload: dict[str, Any]) -> None:
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

    async def handle_context_menu_request(
        self, payload: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
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
