import unittest

from pyrite_sdk.api.data import Theme


class FakeBridge:
    def __init__(self):
        self.calls = []

    def push_wait_response(self, envelope, callback=None, client=None):
        self.calls.append((envelope, callback, client))


class ThemeApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.bridge = FakeBridge()
        self.theme = Theme(self.bridge)

    def assert_last_request(self, type_, payload, callback) -> None:
        envelope, actual_callback, client = self.bridge.calls[-1]
        self.assertEqual(envelope.type, type_)
        self.assertEqual(envelope.payload, payload)
        self.assertIs(actual_callback, callback)
        self.assertIsNone(client)

    def test_theme_api_keeps_original_payload_shape(self) -> None:
        callback = lambda **_: None
        self.theme.contribute("nord", {"color.primary": "#5e81ac"}, callback)
        self.assert_last_request(
            "sdk.theme.contribute",
            {"name": "nord", "data": {"color.primary": "#5e81ac"}},
            callback,
        )

    def test_theme_contribute_adds_terminal_fields(self) -> None:
        callback = lambda **_: None
        ansi = [f"#{index:06x}" for index in range(16)]
        self.theme.contribute(
            "nord",
            {"color.primary": "#5e81ac"},
            terminal_foreground="#eceff4",
            terminal_background=0xFF2E3440,
            terminal_ansi=ansi,
            callback=callback,
        )
        self.assert_last_request(
            "sdk.theme.contribute",
            {
                "name": "nord",
                "data": {
                    "color.primary": "#5e81ac",
                    "terminal.foreground": "#eceff4",
                    "terminal.background": 0xFF2E3440,
                    "terminal.ansi": ansi,
                },
            },
            callback,
        )

    def test_theme_register_runtime_uses_runtime_command(self) -> None:
        callback = lambda **_: None
        self.theme.register_runtime(
            "nord",
            {},
            terminal_foreground="#ffffff",
            callback=callback,
        )
        self.assert_last_request(
            "sdk.theme.register_runtime",
            {
                "name": "nord",
                "data": {"terminal.foreground": "#ffffff"},
            },
            callback,
        )

    def test_theme_rejects_non_sixteen_ansi_colors(self) -> None:
        with self.assertRaises(ValueError):
            self.theme.contribute("broken", {}, terminal_ansi=["#000000"])

    def test_theme_rejects_non_mapping_when_terminal_fields_are_used(self) -> None:
        with self.assertRaises(TypeError):
            self.theme.contribute(
                "broken",
                [],
                terminal_background="#000000",
            )


if __name__ == "__main__":
    unittest.main()
