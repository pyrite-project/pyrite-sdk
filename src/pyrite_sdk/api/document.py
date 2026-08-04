from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional, TYPE_CHECKING

from ..models.schema import request

if TYPE_CHECKING:
    from ..core.bridge import Bridge
    from .events import PluginEventBus, Subscription


@dataclass
class Document:
    """A document open in the host editor."""

    document_id: str
    file_path: str
    language_id: Optional[str] = None
    revision: Optional[int] = None
    is_active: bool = False
    line_count: Optional[int] = None
    text: Optional[str] = None

    @classmethod
    def from_json(cls, data: dict) -> "Document":
        return cls(
            document_id=data.get("documentId", ""),
            file_path=data.get("filePath", ""),
            language_id=data.get("languageId"),
            revision=data.get("revision"),
            is_active=bool(data.get("isActive", False)),
            line_count=data.get("lineCount"),
            text=data.get("text"),
        )


@dataclass
class Position:
    line: int
    column: int = 0


@dataclass
class Selection:
    document_id: str
    start: int
    end: int
    cursor: Optional[Position] = None

    @classmethod
    def from_json(cls, data: dict) -> "Selection":
        cursor = data.get("cursor")
        return cls(
            document_id=data.get("documentId", ""),
            start=int(data.get("start", 0)),
            end=int(data.get("end", 0)),
            cursor=Position(
                line=int(cursor.get("line", 0)),
                column=int(cursor.get("column", 0)),
            )
            if isinstance(cursor, dict)
            else None,
        )


@dataclass
class DocumentSymbol:
    """A symbol reported by the language service.

    Handles both hierarchical ``DocumentSymbol`` (with ``children``) and flat
    ``SymbolInformation`` (with ``location``) shapes, since the host forwards
    raw LSP results.
    """

    name: str
    kind: int
    detail: Optional[str] = None
    children: list["DocumentSymbol"] = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_json(cls, data: dict) -> "DocumentSymbol":
        children = [
            cls.from_json(child)
            for child in data.get("children", [])
            if isinstance(child, dict)
        ]
        return cls(
            name=str(data.get("name", "")),
            kind=int(data.get("kind", 0)),
            detail=data.get("detail"),
            children=children,
            raw=data,
        )


@dataclass
class SymbolResult:
    """Result of a symbols query, tagged with the revision it was computed at.

    ``stale`` is True when the document changed between the request and the
    response, so a plugin can discard results that no longer match the buffer.
    """

    document_id: str
    revision: Optional[int]
    stale: bool
    symbols: list[DocumentSymbol]

    @classmethod
    def from_json(cls, data: dict) -> "SymbolResult":
        return cls(
            document_id=data.get("documentId", ""),
            revision=data.get("revision"),
            stale=bool(data.get("stale", False)),
            symbols=[
                DocumentSymbol.from_json(s)
                for s in data.get("symbols", [])
                if isinstance(s, dict)
            ],
        )


class StaleRevisionError(Exception):
    """Raised when a symbol result is older than the current buffer."""


class EditorDocuments:
    """Host document queries and lifecycle subscriptions for a plugin.

    Wraps the ``sdk.editor.document.*`` request/response commands and the
    ``editor.document.*`` event topics behind typed helpers.
    """

    def __init__(self, bridge: "Bridge", events: "PluginEventBus"):
        self._bridge = bridge
        self._events = events

    # -- Queries ------------------------------------------------------------

    def get_active(self, callback: Optional[Callable] = None) -> None:
        """Fetch the active document. ``callback(document=Document|None)``."""

        def _cb(data=None, error=None, **_):
            if callback is None:
                return
            if error is not None:
                callback(error=error)
                return
            callback(document=Document.from_json(data) if data else None)

        self._bridge.push_wait_response(
            request("sdk.editor.active_document.get", payload={}),
            callback=_cb,
        )

    def get(self, document_id: str, callback: Optional[Callable] = None) -> None:
        def _cb(data=None, error=None, **_):
            if callback is None:
                return
            if error is not None:
                callback(error=error)
                return
            callback(document=Document.from_json(data) if data else None)

        self._bridge.push_wait_response(
            request(
                "sdk.editor.document.get",
                payload={"documentId": document_id},
            ),
            callback=_cb,
        )

    def symbols(
        self, document_id: str, callback: Optional[Callable] = None
    ) -> None:
        """Request document symbols. ``callback(result=SymbolResult)`` or
        ``callback(error=...)`` — the error carries code ``unavailable`` when
        the language service is off."""

        def _cb(data=None, error=None, **_):
            if callback is None:
                return
            if error is not None:
                callback(error=error)
                return
            callback(result=SymbolResult.from_json(data or {}))

        self._bridge.push_wait_response(
            request(
                "sdk.editor.document.symbols",
                payload={"documentId": document_id},
            ),
            callback=_cb,
        )

    def get_selection(
        self, document_id: Optional[str] = None, callback: Optional[Callable] = None
    ) -> None:
        payload: dict[str, Any] = {}
        if document_id is not None:
            payload["documentId"] = document_id

        def _cb(data=None, error=None, **_):
            if callback is None:
                return
            if error is not None:
                callback(error=error)
                return
            callback(selection=Selection.from_json(data) if data else None)

        self._bridge.push_wait_response(
            request("sdk.editor.document.selection.get", payload=payload),
            callback=_cb,
        )

    def reveal(
        self,
        document_id: str,
        line: int,
        column: Optional[int] = None,
        callback: Optional[Callable] = None,
    ) -> None:
        payload: dict[str, Any] = {"documentId": document_id, "line": line}
        if column is not None:
            payload["column"] = column
        self._bridge.push_wait_response(
            request("sdk.editor.document.reveal", payload=payload),
            callback=callback,
        )

    # -- Subscriptions ------------------------------------------------------

    def on_active_changed(self, handler, **kwargs) -> "Subscription":
        return self._events.subscribe(
            "editor.activeDocument.changed", handler, **kwargs
        )

    def on_opened(self, handler, **kwargs) -> "Subscription":
        return self._events.subscribe("editor.document.opened", handler, **kwargs)

    def on_changed(self, handler, **kwargs) -> "Subscription":
        return self._events.subscribe("editor.document.changed", handler, **kwargs)

    def on_saved(self, handler, **kwargs) -> "Subscription":
        return self._events.subscribe("editor.document.saved", handler, **kwargs)

    def on_closed(self, handler, **kwargs) -> "Subscription":
        return self._events.subscribe("editor.document.closed", handler, **kwargs)

    def on_selection_changed(self, handler, **kwargs) -> "Subscription":
        return self._events.subscribe(
            "editor.document.selection.changed", handler, **kwargs
        )
