from __future__ import annotations
from typing import Callable, Optional, Any, TYPE_CHECKING
from ...models.schema import request

if TYPE_CHECKING:
    from ...core.bridge import Bridge


class ThemeSettings:
    """Appearance and style settings."""

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

    def get_mode(self, callback: Optional[Callable] = None):
        self._get("theme.mode", callback)

    def set_mode(self, value: str, callback: Optional[Callable] = None):
        self._set("theme.mode", value, callback)

    def get_style(self, callback: Optional[Callable] = None):
        self._get("theme.style", callback)

    def set_style(self, value: str, callback: Optional[Callable] = None):
        self._set("theme.style", value, callback)

    def get_color(self, callback: Optional[Callable] = None):
        self._get("theme.color", callback)

    def set_color(self, value: Optional[int], callback: Optional[Callable] = None):
        self._set("theme.color", value, callback)

    def get_active_plugin_theme_id(self, callback: Optional[Callable] = None):
        self._get("theme.active_plugin_theme_id", callback)

    def set_active_plugin_theme_id(
        self,
        value: Optional[str],
        callback: Optional[Callable] = None,
    ):
        self._set("theme.active_plugin_theme_id", value, callback)

    def get_use_material_context_menu(self, callback: Optional[Callable] = None):
        self._get("theme.use_material_context_menu", callback)

    def set_use_material_context_menu(
        self,
        value: bool,
        callback: Optional[Callable] = None,
    ):
        self._set("theme.use_material_context_menu", value, callback)


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

    def get_code_folding(self, callback: Optional[Callable] = None): self._get("editor.code_folding", callback)
    def set_code_folding(self, value: bool, callback: Optional[Callable] = None): self._set("editor.code_folding", value, callback)
    def get_guide_lines(self, callback: Optional[Callable] = None): self._get("editor.guide_lines", callback)
    def set_guide_lines(self, value: bool, callback: Optional[Callable] = None): self._set("editor.guide_lines", value, callback)
    def get_local_suggestions(self, callback: Optional[Callable] = None): self._get("editor.local_suggestions", callback)
    def set_local_suggestions(self, value: bool, callback: Optional[Callable] = None): self._set("editor.local_suggestions", value, callback)
    def get_keyboard_suggestions(self, callback: Optional[Callable] = None): self._get("editor.keyboard_suggestions", callback)
    def set_keyboard_suggestions(self, value: bool, callback: Optional[Callable] = None): self._set("editor.keyboard_suggestions", value, callback)
    def get_use_space_as_tab(self, callback: Optional[Callable] = None): self._get("editor.use_space_as_tab", callback)
    def set_use_space_as_tab(self, value: bool, callback: Optional[Callable] = None): self._set("editor.use_space_as_tab", value, callback)
    def get_tab_size(self, callback: Optional[Callable] = None): self._get("editor.tab_size", callback)
    def set_tab_size(self, value: int, callback: Optional[Callable] = None): self._set("editor.tab_size", value, callback)
    def get_gutter_divider(self, callback: Optional[Callable] = None): self._get("editor.gutter_divider", callback)
    def set_gutter_divider(self, value: bool, callback: Optional[Callable] = None): self._set("editor.gutter_divider", value, callback)


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

    def get_semantic_highlighting(self, callback: Optional[Callable] = None): self._get("lsp.semantic_highlighting", callback)
    def set_semantic_highlighting(self, value: bool, callback: Optional[Callable] = None): self._set("lsp.semantic_highlighting", value, callback)
    def get_code_completion(self, callback: Optional[Callable] = None): self._get("lsp.code_completion", callback)
    def set_code_completion(self, value: bool, callback: Optional[Callable] = None): self._set("lsp.code_completion", value, callback)
    def get_hover_info(self, callback: Optional[Callable] = None): self._get("lsp.hover_info", callback)
    def set_hover_info(self, value: bool, callback: Optional[Callable] = None): self._set("lsp.hover_info", value, callback)
    def get_code_action(self, callback: Optional[Callable] = None): self._get("lsp.code_action", callback)
    def set_code_action(self, value: bool, callback: Optional[Callable] = None): self._set("lsp.code_action", value, callback)
    def get_signature_help(self, callback: Optional[Callable] = None): self._get("lsp.signature_help", callback)
    def set_signature_help(self, value: bool, callback: Optional[Callable] = None): self._set("lsp.signature_help", value, callback)
    def get_document_color(self, callback: Optional[Callable] = None): self._get("lsp.document_color", callback)
    def set_document_color(self, value: bool, callback: Optional[Callable] = None): self._set("lsp.document_color", value, callback)
    def get_document_highlight(self, callback: Optional[Callable] = None): self._get("lsp.document_highlight", callback)
    def set_document_highlight(self, value: bool, callback: Optional[Callable] = None): self._set("lsp.document_highlight", value, callback)
    def get_code_folding(self, callback: Optional[Callable] = None): self._get("lsp.code_folding", callback)
    def set_code_folding(self, value: bool, callback: Optional[Callable] = None): self._set("lsp.code_folding", value, callback)
    def get_inlay_hint(self, callback: Optional[Callable] = None): self._get("lsp.inlay_hint", callback)
    def set_inlay_hint(self, value: bool, callback: Optional[Callable] = None): self._set("lsp.inlay_hint", value, callback)
    def get_go_to_definition(self, callback: Optional[Callable] = None): self._get("lsp.go_to_definition", callback)
    def set_go_to_definition(self, value: bool, callback: Optional[Callable] = None): self._set("lsp.go_to_definition", value, callback)
    def get_rename(self, callback: Optional[Callable] = None): self._get("lsp.rename", callback)
    def set_rename(self, value: bool, callback: Optional[Callable] = None): self._set("lsp.rename", value, callback)


class SerialSettings:
    def __init__(self, bridge: Bridge): self._bridge = bridge
    def _get(self, name: str, callback: Optional[Callable] = None): self._bridge.push_wait_response(request("sdk.settings.get", payload={"name": name}), callback=callback)
    def _set(self, name: str, value: Any, callback: Optional[Callable] = None): self._bridge.push_wait_response(request("sdk.settings.set", payload={"name": name, "value": value}), callback=callback)
    def get_default_baud_rate(self, callback: Optional[Callable] = None): self._get("serial.default_baud_rate", callback)
    def set_default_baud_rate(self, value: int, callback: Optional[Callable] = None): self._set("serial.default_baud_rate", value, callback)
    def get_auto_reconnect(self, callback: Optional[Callable] = None): self._get("serial.auto_reconnect", callback)
    def set_auto_reconnect(self, value: bool, callback: Optional[Callable] = None): self._set("serial.auto_reconnect", value, callback)


class TerminalSettings:
    def __init__(self, bridge: Bridge): self._bridge = bridge
    def _get(self, name: str, callback: Optional[Callable] = None): self._bridge.push_wait_response(request("sdk.settings.get", payload={"name": name}), callback=callback)
    def _set(self, name: str, value: Any, callback: Optional[Callable] = None): self._bridge.push_wait_response(request("sdk.settings.set", payload={"name": name, "value": value}), callback=callback)
    def get_font_family(self, callback: Optional[Callable] = None): self._get("terminal.font_family", callback)
    def set_font_family(self, value: str, callback: Optional[Callable] = None): self._set("terminal.font_family", value, callback)
    def get_font_size(self, callback: Optional[Callable] = None): self._get("terminal.font_size", callback)
    def set_font_size(self, value: float, callback: Optional[Callable] = None): self._set("terminal.font_size", value, callback)
    def get_line_height(self, callback: Optional[Callable] = None): self._get("terminal.line_height", callback)
    def set_line_height(self, value: float, callback: Optional[Callable] = None): self._set("terminal.line_height", value, callback)


class MicroPythonStubsSettings:
    def __init__(self, bridge: Bridge): self._bridge = bridge
    def _get(self, name: str, callback: Optional[Callable] = None): self._bridge.push_wait_response(request("sdk.settings.get", payload={"name": name}), callback=callback)
    def _set(self, name: str, value: Any, callback: Optional[Callable] = None): self._bridge.push_wait_response(request("sdk.settings.set", payload={"name": name, "value": value}), callback=callback)
    def get_enabled(self, callback: Optional[Callable] = None): self._get("micropython.stubs.enabled", callback)
    def set_enabled(self, value: bool, callback: Optional[Callable] = None): self._set("micropython.stubs.enabled", value, callback)
    def get_auto_detect_layers(self, callback: Optional[Callable] = None): self._get("micropython.stubs.auto_detect_layers", callback)
    def set_auto_detect_layers(self, value: bool, callback: Optional[Callable] = None): self._set("micropython.stubs.auto_detect_layers", value, callback)
    def get_layers(self, callback: Optional[Callable] = None): self._get("micropython.stubs.layers", callback)
    def set_layers(self, value: list[dict[str, str]], callback: Optional[Callable] = None): self._set("micropython.stubs.layers", value, callback)
    def get_extra_paths(self, callback: Optional[Callable] = None): self._get("micropython.stubs.extra_paths", callback)
    def set_extra_paths(self, value: list[str], callback: Optional[Callable] = None): self._set("micropython.stubs.extra_paths", value, callback)


class Settings:
    def __init__(self, bridge: Bridge):
        self._bridge = bridge
        self.theme = ThemeSettings(bridge)
        self.editor = EditorSettings(bridge)
        self.lsp = LspSettings(bridge)
        self.serial = SerialSettings(bridge)
        self.terminal = TerminalSettings(bridge)
        self.micropython_stubs = MicroPythonStubsSettings(bridge)

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
