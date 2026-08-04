import unittest

from pyrite_sdk.api.clipboard import Clipboard


class FakeBridge:
    def __init__(self):
        self.calls = []

    def push_wait_response(self, envelope, callback=None, client=None):
        self.calls.append((envelope, callback, client))


class ClipboardApiTest(unittest.TestCase):
    def test_set_text_sends_clipboard_request(self) -> None:
        bridge = FakeBridge()
        callback = lambda **_: None

        Clipboard(bridge).set_text("42", callback=callback)

        envelope, actual_callback, client = bridge.calls[0]

        self.assertEqual(envelope.type, "sdk.clipboard.set_text")
        self.assertEqual(envelope.payload, {"text": "42"})
        self.assertIs(actual_callback, callback)
        self.assertIsNone(client)


if __name__ == "__main__":
    unittest.main()
