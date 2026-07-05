import unittest

from pyrite_sdk.api.dialog import Dialog


class FakeBridge:
    def __init__(self):
        self.calls = []

    def push_wait_response(self, envelope, callback=None, client=None):
        self.calls.append((envelope, callback, client))


class DialogApiTest(unittest.TestCase):
    def test_open_folder_sends_dialog_request(self) -> None:
        bridge = FakeBridge()
        callback = lambda **_: None

        Dialog(bridge).open_folder(
            title="Select project",
            initial_directory="/tmp",
            callback=callback,
        )

        envelope, actual_callback, client = bridge.calls[0]

        self.assertEqual(envelope.type, "sdk.dialog.open_folder")
        self.assertEqual(
            envelope.payload,
            {"title": "Select project", "initial_directory": "/tmp"},
        )
        self.assertIs(actual_callback, callback)
        self.assertIsNone(client)


if __name__ == "__main__":
    unittest.main()
