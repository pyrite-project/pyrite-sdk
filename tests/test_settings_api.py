import unittest

from pyrite_sdk.api.settings import Settings, ThemeSettings


class FakeBridge:
    def __init__(self):
        self.calls = []

    def push_wait_response(self, envelope, callback=None, client=None):
        self.calls.append((envelope, callback, client))


class ThemeSettingsApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.bridge = FakeBridge()
        self.settings = ThemeSettings(self.bridge)

    def assert_last_request(self, type_, payload, callback) -> None:
        envelope, actual_callback, client = self.bridge.calls[-1]
        self.assertEqual(envelope.type, type_)
        self.assertEqual(envelope.payload, payload)
        self.assertIs(actual_callback, callback)
        self.assertIsNone(client)

    def test_getters_send_theme_setting_names(self) -> None:
        methods = {
            "get_mode": "theme.mode",
            "get_style": "theme.style",
            "get_color": "theme.color",
            "get_active_plugin_theme_id": "theme.active_plugin_theme_id",
            "get_use_material_context_menu": "theme.use_material_context_menu",
        }

        for method_name, setting_name in methods.items():
            with self.subTest(method=method_name):
                callback = lambda **_: None
                getattr(self.settings, method_name)(callback=callback)
                self.assert_last_request(
                    "sdk.settings.get",
                    {"name": setting_name},
                    callback,
                )

    def test_setters_send_theme_setting_values(self) -> None:
        calls = [
            ("set_mode", "theme.mode", "dark"),
            ("set_style", "theme.style", "compact"),
            ("set_color", "theme.color", 0xFF008080),
            (
                "set_active_plugin_theme_id",
                "theme.active_plugin_theme_id",
                "example::nord",
            ),
            (
                "set_use_material_context_menu",
                "theme.use_material_context_menu",
                True,
            ),
        ]

        for method_name, setting_name, value in calls:
            with self.subTest(method=method_name):
                callback = lambda **_: None
                getattr(self.settings, method_name)(value, callback=callback)
                self.assert_last_request(
                    "sdk.settings.set",
                    {"name": setting_name, "value": value},
                    callback,
                )

    def test_nullable_theme_values_can_be_cleared(self) -> None:
        callback = lambda **_: None

        self.settings.set_color(None, callback=callback)
        self.assert_last_request(
            "sdk.settings.set",
            {"name": "theme.color", "value": None},
            callback,
        )

        self.settings.set_active_plugin_theme_id(None, callback=callback)
        self.assert_last_request(
            "sdk.settings.set",
            {"name": "theme.active_plugin_theme_id", "value": None},
            callback,
        )

    def test_settings_exposes_theme_group(self) -> None:
        settings = Settings(self.bridge)

        self.assertIsInstance(settings.theme, ThemeSettings)


class FakeSettingsHostBridge:
    """Stand-in for the host settings registry, including its name lookup."""

    def __init__(self) -> None:
        self.settings = {"lsp.show_inlay_hints": True}
        self.calls = []
        self.errors = []

    def push_wait_response(self, envelope, callback=None, client=None):
        self.calls.append((envelope, callback, client))
        name = envelope.payload.get("name")
        if name not in self.settings:
            error = LookupError(f"未知设置: {name}")
            self.errors.append(error)
            if callback is not None:
                callback(error=error)
            return
        if envelope.type == "sdk.settings.get":
            if callback is not None:
                callback(name=name, value=self.settings[name])
            return
        if envelope.type == "sdk.settings.set":
            self.settings[name] = envelope.payload.get("value")
            if callback is not None:
                callback(True)


class LspInlayHintSettingsApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.bridge = FakeSettingsHostBridge()
        self.settings = Settings(self.bridge).lsp

    def assert_last_request(self, type_, payload) -> None:
        envelope, _, client = self.bridge.calls[-1]
        self.assertEqual(envelope.type, type_)
        self.assertEqual(envelope.payload, payload)
        self.assertIsNone(client)

    def test_get_inlay_hint_reads_host_setting(self) -> None:
        results = []
        self.settings.get_inlay_hint(
            callback=lambda **kwargs: results.append(kwargs),
        )

        self.assertEqual(self.bridge.errors, [])
        self.assert_last_request(
            "sdk.settings.get",
            {"name": "lsp.show_inlay_hints"},
        )
        self.assertEqual(
            results,
            [{"name": "lsp.show_inlay_hints", "value": True}],
        )

    def test_set_inlay_hint_writes_host_setting(self) -> None:
        results = []
        self.settings.set_inlay_hint(
            False,
            callback=lambda value=None, **_: results.append(value),
        )

        self.assertEqual(self.bridge.errors, [])
        self.assert_last_request(
            "sdk.settings.set",
            {"name": "lsp.show_inlay_hints", "value": False},
        )
        self.assertEqual(results, [True])
        self.assertFalse(self.bridge.settings["lsp.show_inlay_hints"])


if __name__ == "__main__":
    unittest.main()
