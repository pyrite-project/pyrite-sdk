import unittest

from pyrite_sdk.api.tab import TabViewInstance, Tabs


class FakeBridge:
    def __init__(self):
        self.calls = []

    def push_wait_response(self, envelope, callback=None, client=None):
        self.calls.append((envelope, callback, client))


class TabApiTest(unittest.TestCase):
    def setUp(self):
        self.bridge = FakeBridge()
        self.tabs = Tabs(self.bridge)

    def last(self):
        envelope, callback, _ = self.bridge.calls[-1]
        return envelope, callback

    def test_create_main_view_tab(self):
        self.tabs.create_view("debug-enhanced.outline", title="Outline")
        envelope, _ = self.last()
        self.assertEqual(envelope.type, "sdk.tab.create_view")
        self.assertEqual(
            envelope.payload,
            {
                "viewId": "debug-enhanced.outline",
                "title": "Outline",
                "expansion": False,
            },
        )

    def test_create_expansion_view_tab(self):
        self.tabs.create_view("debug-enhanced.outline", expansion=True)
        envelope, _ = self.last()
        self.assertTrue(envelope.payload["expansion"])
        self.assertNotIn("title", envelope.payload)

    def test_success_returns_typed_instance(self):
        received = {}
        self.tabs.create_view(
            "debug-enhanced.outline",
            callback=lambda instance=None, error=None: received.update(
                instance=instance, error=error
            ),
        )
        _, callback = self.last()
        callback(
            data={
                "pluginId": "debug-enhanced",
                "sessionId": "session-1",
                "viewId": "debug-enhanced.outline",
                "instanceId": "tab:1",
            }
        )
        self.assertEqual(
            received["instance"],
            TabViewInstance(
                plugin_id="debug-enhanced",
                session_id="session-1",
                view_id="debug-enhanced.outline",
                instance_id="tab:1",
            ),
        )
        self.assertIsNone(received["error"])

    def test_error_is_forwarded(self):
        received = {}
        self.tabs.create_view(
            "debug-enhanced.outline",
            callback=lambda instance=None, error=None: received.update(
                instance=instance, error=error
            ),
        )
        _, callback = self.last()
        failure = RuntimeError("permission denied")
        callback(error=failure)
        self.assertIs(received["error"], failure)
        self.assertIsNone(received["instance"])


if __name__ == "__main__":
    unittest.main()
