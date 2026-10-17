import unittest

from pyrite_sdk.api.data import Lsp


class FakeBridge:
    def __init__(self):
        self.calls = []

    def push_wait_response(self, envelope, callback=None, client=None):
        self.calls.append((envelope, callback, client))


def valid_configuration(**overrides):
    configuration = {
        "mode": "sectioned",
        "section": "mylsp",
        "stubs_paths_key": "extraPaths",
        "python_executable_key": "pythonInterpreter",
        "type_checking_mode_key": "typeCheckingMode",
    }
    configuration.update(overrides)
    return configuration


class LspApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.bridge = FakeBridge()
        self.lsp = Lsp(self.bridge)

    def assert_last_request(self, type_, payload, callback) -> None:
        envelope, actual_callback, client = self.bridge.calls[-1]
        self.assertEqual(envelope.type, type_)
        self.assertEqual(envelope.payload, payload)
        self.assertIs(actual_callback, callback)
        self.assertIsNone(client)

    def test_lsp_contribute_sends_profile_payload(self) -> None:
        callback = lambda **_: None
        self.lsp.contribute(
            "mylsp",
            valid_configuration(),
            match={"executables": ["mylsp", "mylsp.exe"]},
            label="MyLSP",
            environment={"MYPYPATH": "{stubsPaths}"},
            callback=callback,
        )
        self.assert_last_request(
            "sdk.lsp.contribute",
            {
                "server_id": "mylsp",
                "label": "MyLSP",
                "match": {"executables": ["mylsp", "mylsp.exe"]},
                "configuration": valid_configuration(),
                "environment": {"MYPYPATH": "{stubsPaths}"},
                "scope": "auto",
            },
            callback,
        )

    def test_lsp_contribute_defaults_optional_fields(self) -> None:
        self.lsp.contribute(
            "mylsp", {"mode": "flat"}, match={"executables": ["mylsp"]}
        )
        self.assert_last_request(
            "sdk.lsp.contribute",
            {
                "server_id": "mylsp",
                "label": "",
                "match": {"executables": ["mylsp"]},
                "configuration": {"mode": "flat"},
                "environment": {},
                "scope": "auto",
            },
            None,
        )

    def test_lsp_contribute_rejects_missing_executable_rules(self) -> None:
        with self.assertRaises(ValueError):
            self.lsp.contribute("mylsp", {"mode": "flat"})

    def test_lsp_contribute_rejects_unknown_mode(self) -> None:
        with self.assertRaises(ValueError):
            self.lsp.contribute(
                "mylsp",
                valid_configuration(mode="magic"),
                match={"executables": ["mylsp"]},
            )

    def test_lsp_contribute_rejects_sectioned_without_section(self) -> None:
        with self.assertRaises(ValueError):
            self.lsp.contribute(
                "mylsp",
                valid_configuration(section=None),
                match={"executables": ["mylsp"]},
            )

    def test_lsp_contribute_rejects_unknown_scope(self) -> None:
        with self.assertRaises(ValueError):
            self.lsp.contribute(
                "mylsp",
                {"mode": "flat"},
                match={"executables": ["mylsp"]},
                scope="magic",
            )

    def test_lsp_register_runtime_rejects_unknown_scope(self) -> None:
        with self.assertRaises(ValueError):
            self.lsp.register_runtime(
                "mylsp",
                {"mode": "flat"},
                match={"executables": ["mylsp"]},
                scope="magic",
            )

    def test_lsp_register_runtime_uses_runtime_command_and_scope(self) -> None:
        callback = lambda **_: None
        self.lsp.register_runtime(
            "mylsp",
            {"mode": "flat", "stubs_paths_key": "extraPaths"},
            match={"executables": ["mylsp"]},
            callback=callback,
        )
        self.assert_last_request(
            "sdk.lsp.register_runtime",
            {
                "server_id": "mylsp",
                "label": "",
                "match": {"executables": ["mylsp"]},
                "configuration": {"mode": "flat", "stubs_paths_key": "extraPaths"},
                "environment": {},
                "scope": "runtime",
            },
            callback,
        )

    def test_lsp_revoke_get_list_keep_original_shapes(self) -> None:
        callback = lambda **_: None
        self.lsp.revoke("mylsp", callback)
        self.assert_last_request(
            "sdk.lsp.revoke", {"server_id": "mylsp"}, callback
        )

        self.lsp.get("mylsp", callback)
        self.assert_last_request(
            "sdk.lsp.get", {"server_id": "mylsp"}, callback
        )

        self.lsp.list(callback)
        self.assert_last_request("sdk.lsp.list", {}, callback)


if __name__ == "__main__":
    unittest.main()
