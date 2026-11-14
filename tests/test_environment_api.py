import unittest

from pyrite_sdk.api.environment import Environment

SNAPSHOT = {
    "os": "linux",
    "isDesktopPlatform": True,
    "layoutMode": "desktop",
    "width": 1440,
    "height": 900,
    "locale": "zh-CN",
    "themeMode": "dark",
}


class FakeBridge:
    """Captures pending requests and replays host responses."""

    def __init__(self):
        self.pushed = []
        self.callback = None

    def push_wait_response(self, envelope, callback=None, client=None):
        self.pushed.append((envelope, callback, client))
        self.callback = callback

    def respond(self, payload):
        # Mirrors Bridge._complete_pending_response for a dict payload.
        self.callback(**payload)

    def respond_positional(self, payload):
        # Mirrors Bridge._complete_pending_response for a non-dict payload.
        self.callback(payload)

    def fail(self, error):
        self.callback(error=error)


class EnvironmentApiTest(unittest.TestCase):
    def test_get_delivers_snapshot_wrapped_in_host_data(self) -> None:
        bridge = FakeBridge()
        env = Environment(bridge)  # type: ignore[arg-type]
        received = []

        env.get(received.append)

        envelope, _, _ = bridge.pushed[0]
        self.assertEqual(envelope.type, "sdk.env.get")
        self.assertEqual(envelope.payload, {})

        bridge.respond({"data": SNAPSHOT})

        self.assertEqual(received, [SNAPSHOT])
        self.assertEqual(env.os, "linux")
        self.assertTrue(env.is_desktop_platform)
        self.assertEqual(env.layout_mode, "desktop")
        self.assertEqual(env.width, 1440)
        self.assertEqual(env.height, 900)
        self.assertEqual(env.locale, "zh-CN")
        self.assertEqual(env.theme_mode, "dark")

    def test_get_without_callback_still_updates_snapshot(self) -> None:
        bridge = FakeBridge()
        env = Environment(bridge)  # type: ignore[arg-type]

        env.get()
        self.assertIsNone(env.layout_mode)

        bridge.respond({"data": SNAPSHOT})

        self.assertEqual(env.os, "linux")
        self.assertEqual(env.layout_mode, "desktop")
        self.assertEqual(env.theme_mode, "dark")

    def test_get_accepts_positional_snapshot(self) -> None:
        bridge = FakeBridge()
        env = Environment(bridge)  # type: ignore[arg-type]
        received = []

        env.get(received.append)
        bridge.respond_positional(SNAPSHOT)

        self.assertEqual(received, [SNAPSHOT])
        self.assertEqual(env.layout_mode, "desktop")

    def test_get_error_response_does_not_invoke_callback(self) -> None:
        bridge = FakeBridge()
        env = Environment(bridge)  # type: ignore[arg-type]
        received = []

        env.get(received.append)
        bridge.fail(RuntimeError("permission_denied"))

        self.assertEqual(received, [])
        self.assertIsNone(env.os)

    def test_get_tolerates_extra_keys_in_response_payload(self) -> None:
        bridge = FakeBridge()
        env = Environment(bridge)  # type: ignore[arg-type]
        received = []

        env.get(received.append)
        bridge.respond({"data": SNAPSHOT, "requestId": "host-request"})

        self.assertEqual(received, [SNAPSHOT])
        self.assertEqual(env.layout_mode, "desktop")


if __name__ == "__main__":
    unittest.main()
