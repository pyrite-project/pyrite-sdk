import unittest

from pyrite_sdk.api.tab import EditorTab, EditorTabs


class FakeBridge:
    def __init__(self):
        self.calls = []

    def push_wait_response(self, envelope, callback=None, client=None):
        self.calls.append((envelope, callback, client))


class EditorTabsTest(unittest.TestCase):
    def setUp(self):
        self.bridge = FakeBridge()
        self.tabs = EditorTabs(self.bridge)

    def last(self):
        envelope, callback, _ = self.bridge.calls[-1]
        return envelope, callback

    def test_list(self):
        received = {}
        self.tabs.list(
            callback=lambda tabs=None, error=None: received.update(
                tabs=tabs,
                error=error,
            )
        )
        envelope, callback = self.last()
        self.assertEqual(envelope.type, "sdk.tab.list")
        callback(
            data=[
                {
                    "index": 2,
                    "tabId": "plugin://demo/main#tab:1",
                    "resource": None,
                    "name": "Main",
                    "kind": "plugin_view",
                    "view": {
                        "pluginId": "demo",
                        "viewId": "demo.main",
                        "instanceId": "tab:1",
                    },
                }
            ]
        )
        self.assertEqual(
            received["tabs"],
            [
                EditorTab(
                    tab_id="plugin://demo/main#tab:1",
                    index=2,
                    name="Main",
                    kind="plugin_view",
                    resource=None,
                    plugin_id="demo",
                    view_id="demo.main",
                    view_instance_id="tab:1",
                )
            ],
        )
        self.assertIsNone(received["error"])

    def test_activate(self):
        self.tabs.activate("plugin://demo/main#tab:1")
        envelope, _ = self.last()
        self.assertEqual(envelope.type, "sdk.tab.activate")
        self.assertEqual(
            envelope.payload,
            {"tab_id": "plugin://demo/main#tab:1"},
        )

    def test_close_forwards_response(self):
        received = {}
        self.tabs.close(
            "file:///workspace/main.py",
            callback=lambda data=None, error=None: received.update(
                data=data,
                error=error,
            ),
        )
        envelope, callback = self.last()
        self.assertEqual(envelope.type, "sdk.tab.close")
        self.assertEqual(envelope.payload, {"tab_id": "file:///workspace/main.py"})
        callback(data=True)
        self.assertTrue(received["data"])
        self.assertIsNone(received["error"])

    def test_tab_id_is_required(self):
        with self.assertRaises(ValueError):
            self.tabs.activate("")
        with self.assertRaises(ValueError):
            self.tabs.close("")


if __name__ == "__main__":
    unittest.main()
