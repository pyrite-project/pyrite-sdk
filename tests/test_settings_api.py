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


if __name__ == "__main__":
    unittest.main()
