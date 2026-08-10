from __future__ import annotations
from typing import Any, Callable, Optional, TYPE_CHECKING
from ...models.schema import (
    request,
    EditorSetTextPayload,
    EditorInsertTextPayload,
    EditorReplaceRangePayload,
    EditorGetLineTextPayload,
    EditorCursorPositionPayload,
    EditorSelectionPayload,
    EditorFindPayload,
    EditorFindRegexPayload,
    EditorOpenFilePayload,
    EditorCloseTabPayload,
    EditorGhostTextPayload,
    EditorScrollToLinePayload,
)
if TYPE_CHECKING:
    from ...core.bridge import Bridge


class Editor:
    def __init__(self, bridge: Bridge) -> None:
        self._bridge: Bridge = bridge

    # ── Text Content ──

    def get_text(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._bridge.push_wait_response(
            request("sdk.editor.get_text"),
            callback=callback,
        )

    def set_text(
        self, text: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.editor.set_text",
                payload=EditorSetTextPayload(text=text),
            ),
            callback=callback,
        )

    def get_line_count(
        self, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._bridge.push_wait_response(
            request("sdk.editor.get_line_count"),
            callback=callback,
        )

    def get_line_text(
        self, line: int, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.editor.get_line_text",
                payload=EditorGetLineTextPayload(line=line),
            ),
            callback=callback,
        )

    def get_selected_text(
        self, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._bridge.push_wait_response(
            request("sdk.editor.get_selected_text"),
            callback=callback,
        )

    def insert_text(
        self, text: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.editor.insert_text",
                payload=EditorInsertTextPayload(text=text),
            ),
            callback=callback,
        )

    def replace_range(
        self,
        start: int,
        end: int,
        text: str,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.editor.replace_range",
                payload=EditorReplaceRangePayload(start=start, end=end, text=text),
            ),
            callback=callback,
        )

    def clear(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._bridge.push_wait_response(
            request("sdk.editor.clear"),
            callback=callback,
        )

    # ── Cursor & Selection ──

    def get_cursor_position(
        self, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._bridge.push_wait_response(
            request("sdk.editor.get_cursor_position"),
            callback=callback,
        )

    def set_cursor_position(
        self,
        line: int,
        column: int,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.editor.set_cursor_position",
                payload=EditorCursorPositionPayload(line=line, column=column),
            ),
            callback=callback,
        )

    def get_selection(
        self, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._bridge.push_wait_response(
            request("sdk.editor.get_selection"),
            callback=callback,
        )

    def set_selection(
        self,
        start: int,
        end: int,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.editor.set_selection",
                payload=EditorSelectionPayload(start=start, end=end),
            ),
            callback=callback,
        )

    def select_all(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._bridge.push_wait_response(
            request("sdk.editor.select_all"),
            callback=callback,
        )

    def go_to_line(
        self, line: int, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.editor.go_to_line",
                payload=EditorGetLineTextPayload(line=line),
            ),
            callback=callback,
        )

    # ── Clipboard ──

    def copy(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._bridge.push_wait_response(
            request("sdk.editor.copy"),
            callback=callback,
        )

    def cut(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._bridge.push_wait_response(
            request("sdk.editor.cut"),
            callback=callback,
        )

    def paste(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._bridge.push_wait_response(
            request("sdk.editor.paste"),
            callback=callback,
        )

    # ── Undo / Redo ──

    def undo(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._bridge.push_wait_response(
            request("sdk.editor.undo"),
            callback=callback,
        )

    def redo(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._bridge.push_wait_response(
            request("sdk.editor.redo"),
            callback=callback,
        )

    def can_undo(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._bridge.push_wait_response(
            request("sdk.editor.can_undo"),
            callback=callback,
        )

    def can_redo(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._bridge.push_wait_response(
            request("sdk.editor.can_redo"),
            callback=callback,
        )

    # ── Search ──

    def find(
        self,
        word: str,
        match_case: bool = False,
        whole_word: bool = False,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.editor.find",
                payload=EditorFindPayload(word=word, match_case=match_case, whole_word=whole_word),
            ),
            callback=callback,
        )

    def find_regex(
        self, pattern: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.editor.find_regex",
                payload=EditorFindRegexPayload(pattern=pattern),
            ),
            callback=callback,
        )

    def clear_search(
        self, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._bridge.push_wait_response(
            request("sdk.editor.clear_search"),
            callback=callback,
        )

    # ── Tab Management ──

    def open_file(
        self, path: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.editor.open_file",
                payload=EditorOpenFilePayload(path=path),
            ),
            callback=callback,
        )

    def close_tab(
        self, path: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.editor.close_tab",
                payload=EditorCloseTabPayload(path=path),
            ),
            callback=callback,
        )

    def get_current_tab(
        self, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._bridge.push_wait_response(
            request("sdk.editor.get_current_tab"),
            callback=callback,
        )

    def list_tabs(
        self, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._bridge.push_wait_response(
            request("sdk.editor.list_tabs"),
            callback=callback,
        )

    # ── Decorations ──

    def set_ghost_text(
        self,
        text: str,
        line: int,
        column: int,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.editor.set_ghost_text",
                payload=EditorGhostTextPayload(text=text, line=line, column=column),
            ),
            callback=callback,
        )

    def clear_ghost_text(
        self, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._bridge.push_wait_response(
            request("sdk.editor.clear_ghost_text"),
            callback=callback,
        )

    def scroll_to_line(
        self, line: int, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.editor.scroll_to_line",
                payload=EditorScrollToLinePayload(line=line),
            ),
            callback=callback,
        )
