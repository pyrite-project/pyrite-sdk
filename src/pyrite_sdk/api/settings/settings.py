from __future__ import annotations
from typing import Callable, Optional, Any, TYPE_CHECKING
from ...models.schema import request

if TYPE_CHECKING:
    from ...core.bridge import Bridge


class EditorSettings:
    """编辑器相关设置"""

    def __init__(self, bridge: Bridge):
        self._bridge = bridge

    def _get(self, name: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request("sdk.settings.get", payload={"name": name}),
            callback=callback,
        )

    def _set(self, name: str, value: Any, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request("sdk.settings.set", payload={"name": name, "value": value}),
            callback=callback,
        )

    def get_font_family(self, callback: Optional[Callable] = None):
        self._get("editor.font_family", callback)

    def set_font_family(self, value: str, callback: Optional[Callable] = None):
        self._set("editor.font_family", value, callback)

    def get_font_size(self, callback: Optional[Callable] = None):
        self._get("editor.font_size", callback)

    def set_font_size(self, value: float, callback: Optional[Callable] = None):
        self._set("editor.font_size", value, callback)

    def get_word_wrap(self, callback: Optional[Callable] = None):
        self._get("editor.word_wrap", callback)

    def set_word_wrap(self, value: bool, callback: Optional[Callable] = None):
        self._set("editor.word_wrap", value, callback)

    def get_line_number(self, callback: Optional[Callable] = None):
        self._get("editor.line_number", callback)

    def set_line_number(self, value: bool, callback: Optional[Callable] = None):
        self._set("editor.line_number", value, callback)

    def get_chinese_to_unicode(self, callback: Optional[Callable] = None):
        self._get("editor.chinese_to_unicode", callback)

    def set_chinese_to_unicode(self, value: bool, callback: Optional[Callable] = None):
        self._set("editor.chinese_to_unicode", value, callback)

    def get_enable_signal_detection(self, callback: Optional[Callable] = None):
        self._get("editor.enable_signal_detection", callback)

    def set_enable_signal_detection(self, value: bool, callback: Optional[Callable] = None):
        self._set("editor.enable_signal_detection", value, callback)

    def get_upload_confirm_style(self, callback: Optional[Callable] = None):
        self._get("editor.upload_confirm_style", callback)

    def set_upload_confirm_style(self, value: str, callback: Optional[Callable] = None):
        self._set("editor.upload_confirm_style", value, callback)

    def get_confirm_shortcut(self, callback: Optional[Callable] = None):
        self._get("editor.confirm_shortcut", callback)

    def set_confirm_shortcut(self, value: str, callback: Optional[Callable] = None):
        self._set("editor.confirm_shortcut", value, callback)

    def get_cancel_shortcut(self, callback: Optional[Callable] = None):
        self._get("editor.cancel_shortcut", callback)

    def set_cancel_shortcut(self, value: str, callback: Optional[Callable] = None):
        self._set("editor.cancel_shortcut", value, callback)


class LspSettings:
    """语言服务器相关设置"""

    def __init__(self, bridge: Bridge):
        self._bridge = bridge

    def _get(self, name: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request("sdk.settings.get", payload={"name": name}),
            callback=callback,
        )

    def _set(self, name: str, value: Any, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request("sdk.settings.set", payload={"name": name, "value": value}),
            callback=callback,
        )

    def get_enabled(self, callback: Optional[Callable] = None):
        self._get("lsp.enabled", callback)

    def set_enabled(self, value: bool, callback: Optional[Callable] = None):
        self._set("lsp.enabled", value, callback)

    def get_type(self, callback: Optional[Callable] = None):
        self._get("lsp.type", callback)

    def set_type(self, value: str, callback: Optional[Callable] = None):
        self._set("lsp.type", value, callback)

    def get_websocket_path(self, callback: Optional[Callable] = None):
        self._get("lsp.websocket_path", callback)

    def set_websocket_path(self, value: str, callback: Optional[Callable] = None):
        self._set("lsp.websocket_path", value, callback)

    def get_stdio_executable(self, callback: Optional[Callable] = None):
        self._get("lsp.stdio_executable", callback)

    def set_stdio_executable(self, value: str, callback: Optional[Callable] = None):
        self._set("lsp.stdio_executable", value, callback)

    def get_stdio_args(self, callback: Optional[Callable] = None):
        self._get("lsp.stdio_args", callback)

    def set_stdio_args(self, value: str, callback: Optional[Callable] = None):
        self._set("lsp.stdio_args", value, callback)

    def get_disable_warning(self, callback: Optional[Callable] = None):
        self._get("lsp.disable_warning", callback)

    def set_disable_warning(self, value: bool, callback: Optional[Callable] = None):
        self._set("lsp.disable_warning", value, callback)

    def get_disable_error(self, callback: Optional[Callable] = None):
        self._get("lsp.disable_error", callback)

    def set_disable_error(self, value: bool, callback: Optional[Callable] = None):
        self._set("lsp.disable_error", value, callback)


class Settings:
    def __init__(self, bridge: Bridge):
        self._bridge = bridge
        self.editor = EditorSettings(bridge)
        self.lsp = LspSettings(bridge)

    def get(self, name: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request("sdk.settings.get", payload={"name": name}),
            callback=callback,
        )

    def set(self, name: str, value: Any, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request("sdk.settings.set", payload={"name": name, "value": value}),
            callback=callback,
        )

    def list(self, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request("sdk.settings.list"),
            callback=callback,
        )
