import json
import unittest
from pathlib import Path

from pyrite_sdk.api.commands import Commands
from pyrite_sdk.models.schema import Envelope


FIXTURE = Path(__file__).parent / "fixtures" / "protocol" / "protocol_v1_commands_configuration.json"


class FakeBridge:
    def __init__(self):
        self.pushed = []

    def push(self, envelope, callback=None, client=None):
        self.pushed.append((envelope, callback))


class CommandsConfigurationTests(unittest.IsolatedAsyncioTestCase):
    def test_fixture_types(self):
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(data["commandExecute"]["type"], "ide.command.execute")
        self.assertEqual(data["configurationGet"]["type"], "sdk.configuration.get")
        self.assertEqual(data["configurationSet"]["type"], "sdk.configuration.set")
        self.assertEqual(data["configurationList"]["type"], "sdk.configuration.list")
        self.assertEqual(
            data["configurationChanged"]["payload"]["topic"],
            "configuration.changed",
        )

    async def test_commands_dispatch_registered_handler(self):
        commands = Commands(FakeBridge())
        seen = {}

        def handler(*, args, context):
            seen["args"] = args
            seen["context"] = context
            return {"ok": True}

        commands.register("debug-enhanced.refreshVariables", handler)
        result = await commands.dispatch(
            "debug-enhanced.refreshVariables",
            {"force": True},
            {"viewId": "debug-enhanced.device-variables"},
        )
        self.assertEqual(result, {"ok": True})
        self.assertEqual(seen["args"], {"force": True})
        self.assertEqual(
            seen["context"]["viewId"],
            "debug-enhanced.device-variables",
        )

    async def test_commands_missing_handler_raises(self):
        commands = Commands(FakeBridge())
        with self.assertRaises(LookupError):
            await commands.dispatch("missing.command")

    def test_commands_dispose_clears_handlers(self):
        commands = Commands(FakeBridge())
        commands.register("a", lambda **_: None)
        commands.dispose_all()
        self.assertEqual(commands._handlers, {})

    def test_fixture_envelope_parses(self):
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        for payload in data.values():
            envelope = Envelope.model_validate(payload)
            self.assertEqual(envelope.protocol_version, 1)


if __name__ == "__main__":
    unittest.main()
