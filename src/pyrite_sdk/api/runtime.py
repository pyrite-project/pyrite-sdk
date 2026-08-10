from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional, TYPE_CHECKING

from ..models.schema import request

if TYPE_CHECKING:
    from ..core.bridge import Bridge
    from .events import EventHandler, PluginEventBus, Subscription


class StaleReferenceError(Exception):
    """Raised when an object reference belongs to a previous runtime generation.

    A backend restart (hardware reset / reconnect) invalidates every reference
    minted before it; querying such a reference fails with error code
    ``stale_reference``, which this exception represents.
    """


class RuntimeUnavailableError(Exception):
    """Raised when the backend cannot inspect safely (capability unavailable).

    Inspection never interrupts a running program, so when the backend has no
    safe way to read state it declines with ``unavailable`` rather than sending
    an interrupt.
    """


@dataclass
class RuntimeSession:
    session_id: str
    generation: int
    capability: str = "available"
    program_state: str = "idle"

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "RuntimeSession":
        return cls(
            session_id=data.get("sessionId", ""),
            generation=int(data.get("generation", 0)),
            capability=data.get("capability", "available"),
            program_state=data.get("programState", "idle"),
        )


@dataclass
class Scope:
    id: str
    name: str
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "Scope":
        return cls(id=str(data.get("id", "")), name=str(data.get("name", "")), raw=data)


@dataclass
class Variable:
    """A variable or object slot, matching the T14 data model."""

    name: str
    type: str
    repr: str
    reference: Optional[str] = None
    has_children: bool = False
    named_variables: int = 0
    indexed_variables: int = 0

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "Variable":
        return cls(
            name=str(data.get("name", "")),
            type=str(data.get("type", "")),
            repr=str(data.get("repr", "")),
            reference=data.get("reference"),
            has_children=bool(data.get("hasChildren", False)),
            named_variables=int(data.get("namedVariables", 0)),
            indexed_variables=int(data.get("indexedVariables", 0)),
        )


@dataclass
class ObjectInfo:
    reference: str
    type: str
    repr: str
    attributes: list[Variable] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "ObjectInfo":
        return cls(
            reference=str(data.get("reference", "")),
            type=str(data.get("type", "")),
            repr=str(data.get("repr", "")),
            attributes=[
                Variable.from_json(a)
                for a in data.get("attributes", [])
                if isinstance(a, dict)
            ],
            raw=data,
        )


@dataclass
class Page:
    """A page of runtime items with optional total and start offset."""

    items: list[Variable]
    total: Optional[int] = None
    start: int = 0


def _error_for(error: Any) -> BaseException:
    """Maps a wire error to a specific runtime exception where applicable."""
    code = getattr(error, "code", None)
    if code == "stale_reference":
        return StaleReferenceError(getattr(error, "message", "stale reference"))
    if code == "unavailable":
        return RuntimeUnavailableError(
            getattr(error, "message", "runtime inspection unavailable")
        )
    return error if isinstance(error, BaseException) else Exception(str(error))


class Runtime:
    """Runtime inspection queries and lifecycle subscriptions for a plugin.

    Children load lazily and are paged via ``start``/``count`` so a large
    container is never returned whole.
    """

    def __init__(self, bridge: "Bridge", events: "PluginEventBus") -> None:
        self._bridge: Bridge = bridge
        self._events: PluginEventBus = events

    # -- Queries ------------------------------------------------------------

    def sessions(self, callback: Optional[Callable[..., Any]] = None) -> None:
        def _cb(data: Any = None, error: Any = None, **_: Any) -> None:
            if callback is None:
                return
            if error is not None:
                callback(error=_error_for(error))
                return
            sessions = [
                RuntimeSession.from_json(s)
                for s in (data or {}).get("sessions", [])
                if isinstance(s, dict)
            ]
            callback(sessions=sessions)

        self._bridge.push_wait_response(
            request("sdk.runtime.sessions", payload={}), callback=_cb
        )

    def state(
        self,
        session_id: Optional[str] = None,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        payload: dict[str, Any] = {}
        if session_id is not None:
            payload["sessionId"] = session_id

        def _cb(data: Any = None, error: Any = None, **_: Any) -> None:
            if callback is None:
                return
            if error is not None:
                callback(error=_error_for(error))
                return
            callback(session=RuntimeSession.from_json(data) if data else None)

        self._bridge.push_wait_response(
            request("sdk.runtime.state", payload=payload), callback=_cb
        )

    def scopes(
        self,
        session_id: str,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        def _cb(data: Any = None, error: Any = None, **_: Any) -> None:
            if callback is None:
                return
            if error is not None:
                callback(error=_error_for(error))
                return
            callback(
                scopes=[
                    Scope.from_json(s)
                    for s in (data or {}).get("items", [])
                    if isinstance(s, dict)
                ]
            )

        self._bridge.push_wait_response(
            request("sdk.runtime.scopes", payload={"sessionId": session_id}),
            callback=_cb,
        )

    def variables(
        self,
        session_id: str,
        scope_id: str,
        start: int = 0,
        count: int = 0,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.runtime.variables",
                payload={
                    "sessionId": session_id,
                    "scopeId": scope_id,
                    "start": start,
                    "count": count,
                },
            ),
            callback=self._variables_cb(callback),
        )

    def children(
        self,
        reference: str,
        start: int = 0,
        count: int = 0,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        """Lazily fetch a paged slice of an object's children."""
        self._bridge.push_wait_response(
            request(
                "sdk.runtime.children",
                payload={"reference": reference, "start": start, "count": count},
            ),
            callback=self._variables_cb(callback),
        )

    def object_info(
        self,
        reference: str,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        def _cb(data: Any = None, error: Any = None, **_: Any) -> None:
            if callback is None:
                return
            if error is not None:
                callback(error=_error_for(error))
                return
            callback(info=ObjectInfo.from_json(data) if data else None)

        self._bridge.push_wait_response(
            request("sdk.runtime.object_info", payload={"reference": reference}),
            callback=_cb,
        )

    def _variables_cb(
        self, callback: Optional[Callable[..., Any]]
    ) -> Callable[..., None]:
        def _cb(data: Any = None, error: Any = None, **_: Any) -> None:
            if callback is None:
                return
            if error is not None:
                callback(error=_error_for(error))
                return
            data = data or {}
            page = Page(
                items=[
                    Variable.from_json(v)
                    for v in data.get("items", [])
                    if isinstance(v, dict)
                ],
                total=data.get("total"),
                start=int(data.get("start", 0)),
            )
            callback(page=page)

        return _cb

    # -- Subscriptions ------------------------------------------------------

    def on_session_created(
        self, handler: "EventHandler", **kwargs: Any
    ) -> "Subscription":
        return self._events.subscribe("runtime.session.created", handler, **kwargs)

    def on_session_ended(
        self, handler: "EventHandler", **kwargs: Any
    ) -> "Subscription":
        return self._events.subscribe("runtime.session.ended", handler, **kwargs)

    def on_session_state_changed(
        self, handler: "EventHandler", **kwargs: Any
    ) -> "Subscription":
        return self._events.subscribe(
            "runtime.session.state.changed", handler, **kwargs
        )

    def on_program_started(
        self, handler: "EventHandler", **kwargs: Any
    ) -> "Subscription":
        return self._events.subscribe("runtime.program.started", handler, **kwargs)

    def on_program_paused(
        self, handler: "EventHandler", **kwargs: Any
    ) -> "Subscription":
        return self._events.subscribe("runtime.program.paused", handler, **kwargs)

    def on_program_resumed(
        self, handler: "EventHandler", **kwargs: Any
    ) -> "Subscription":
        return self._events.subscribe("runtime.program.resumed", handler, **kwargs)

    def on_program_finished(
        self, handler: "EventHandler", **kwargs: Any
    ) -> "Subscription":
        return self._events.subscribe("runtime.program.finished", handler, **kwargs)

    def on_backend_restarted(
        self, handler: "EventHandler", **kwargs: Any
    ) -> "Subscription":
        return self._events.subscribe("runtime.backend.restarted", handler, **kwargs)

    def on_variables_changed(
        self, handler: "EventHandler", **kwargs: Any
    ) -> "Subscription":
        return self._events.subscribe("runtime.variables.changed", handler, **kwargs)
