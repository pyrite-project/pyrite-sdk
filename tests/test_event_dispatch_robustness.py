import asyncio
import unittest
from types import SimpleNamespace

from pyrite_sdk.api.configuration import Configuration
from pyrite_sdk.api.environment import Environment
from pyrite_sdk.api.events import PluginEventBus
from pyrite_sdk.core.bridge import Bridge
from pyrite_sdk.models.schema import Envelope
from tests.fakes import ClientTransport, FakeClient


async def _wait_until(predicate, timeout=1.0):
    async with asyncio.timeout(timeout):
        while not predicate():
            await asyncio.sleep(0)


class FakeBridge:
    def __init__(self):
        self.calls = []
        self.logs = []
        self.errors = []

    def push_wait_response(self, envelope, callback=None, client=None):
        self.calls.append((envelope, callback, client))

    def _log_internal(self, *args):
        self.logs.append(" ".join(str(arg) for arg in args))

    def report_error(self, message, **details):
        self.errors.append((message, details))


class ConfigurationChangedDispatchTest(unittest.IsolatedAsyncioTestCase):
    async def test_on_changed_receives_single_event_dict(self):
        bridge = FakeBridge()
        bus = PluginEventBus(bridge)  # type: ignore[arg-type]
        configuration = Configuration(bridge, bus)  # type: ignore[arg-type]
        received = []

        subscription = configuration.on_changed(received.append)
        await bus.dispatch(
            subscription.id,
            "configuration.changed",
            [{"id": "theme", "value": "dark"}],
        )

        self.assertEqual(received, [{"id": "theme", "value": "dark"}])
        self.assertEqual(bridge.errors, [])

    async def test_on_changed_filters_single_event_by_id(self):
        bridge = FakeBridge()
        bus = PluginEventBus(bridge)  # type: ignore[arg-type]
        configuration = Configuration(bridge, bus)  # type: ignore[arg-type]
        received = []

        subscription = configuration.on_changed(
            received.append, configuration_id="theme"
        )
        await bus.dispatch(
            subscription.id,
            "configuration.changed",
            [{"id": "other", "value": 1}],
        )
        await bus.dispatch(
            subscription.id,
            "configuration.changed",
            [{"id": "theme", "value": "light"}],
        )

        self.assertEqual(received, [{"id": "theme", "value": "light"}])


class EnvironmentChangeDispatchTest(unittest.TestCase):
    def test_raising_handler_does_not_stop_later_handlers(self):
        bridge = FakeBridge()
        environment = Environment(bridge)  # type: ignore[arg-type]
        received = []

        def bad_change(snapshot):
            raise RuntimeError("environment handler boom")

        def good_change(snapshot):
            received.append(snapshot)

        environment.on_change(bad_change)
        environment.on_change(good_change)

        environment._handle_change({"layoutMode": "tablet"})

        self.assertEqual(received, [{"layoutMode": "tablet"}])
        self.assertEqual(environment.layout_mode, "tablet")
        self.assertEqual(len(bridge.errors), 1)
        self.assertIn("environment handler boom", bridge.logs[0])
        self.assertEqual(bridge.errors[0][1]["source"], "ide.env.changed")


class BridgeEnvironmentChangeDispatchTest(unittest.IsolatedAsyncioTestCase):
    def _bridge(self):
        plugin = SimpleNamespace(pages={})
        bridge = Bridge(plugin, transport=ClientTransport())
        plugin.env = Environment(bridge)
        bridge._handshake_state = "ready"
        bridge.asyncio_loop = asyncio.get_running_loop()
        bridge.message_queue = asyncio.Queue(maxsize=16)
        logs = []
        bridge._log_internal = lambda *args: logs.append(
            " ".join(str(arg) for arg in args)
        )
        return bridge, plugin, logs

    async def test_handler_exception_does_not_stop_later_env_frames(self):
        bridge, plugin, logs = self._bridge()
        received = []

        def bad_change(snapshot):
            raise RuntimeError("environment handler boom")

        plugin.env.on_change(bad_change)
        plugin.env.on_change(received.append)

        first = Envelope(
            type="ide.env.changed",
            plugin_id=bridge.plugin_id,
            session_id=bridge.session_id,
            generation=bridge.generation,
            sequence=1,
            payload={"layoutMode": "tablet"},
        )
        second = Envelope(
            type="ide.env.changed",
            plugin_id=bridge.plugin_id,
            session_id=bridge.session_id,
            generation=bridge.generation,
            sequence=2,
            payload={"layoutMode": "mobile"},
        )
        client = FakeClient(
            [
                first.model_dump_json(by_alias=True),
                second.model_dump_json(by_alias=True),
            ]
        )

        await bridge.handler(client)
        await _wait_until(lambda: bridge.message_queue.qsize() >= 1)

        self.assertEqual(
            received,
            [{"layoutMode": "tablet"}, {"layoutMode": "mobile"}],
        )
        self.assertFalse(
            any("Bridge handler error" in line for line in logs)
        )
        _, report = bridge.message_queue.get_nowait()
        self.assertEqual(report.type, "sdk.runtime.report_error")
        self.assertIn(
            "environment handler boom", report.payload["traceback"]
        )
        self.assertEqual(report.payload["source"], "ide.env.changed")


if __name__ == "__main__":
    unittest.main()
