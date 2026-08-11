import unittest

from pyrite_sdk.api.dialog import Dialog


class FakeBridge:
    def __init__(self):
        self.calls = []

    def push_wait_response(self, envelope, callback=None, client=None):
        self.calls.append((envelope, callback, client))


class DialogApiTest(unittest.TestCase):
    def assert_dialog_request(self, method_name: str, command: str) -> None:
        bridge = FakeBridge()
        callback = lambda **_: None

        getattr(Dialog(bridge), method_name)(
            title="Select project",
            initial_directory="/tmp",
            callback=callback,
        )

        envelope, actual_callback, client = bridge.calls[0]

        self.assertEqual(envelope.type, command)
        self.assertEqual(
            envelope.payload,
            {"title": "Select project", "initial_directory": "/tmp"},
        )
        self.assertIs(actual_callback, callback)
        self.assertIsNone(client)

    def test_open_folder_sends_dialog_request(self) -> None:
        self.assert_dialog_request("open_folder", "sdk.dialog.open_folder")

    def test_open_file_sends_dialog_request(self) -> None:
        self.assert_dialog_request("open_file", "sdk.dialog.open_file")

    def test_open_files_sends_dialog_request(self) -> None:
        self.assert_dialog_request("open_files", "sdk.dialog.open_files")


if __name__ == "__main__":
    unittest.main()
