import asyncio
import unittest
import warnings
from types import SimpleNamespace

from pyrite_sdk.api.configuration import Configuration
from pyrite_sdk.api.environment import Environment
from pyrite_sdk.api.events import PluginEventBus
from pyrite_sdk.api.view import Views
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


class BridgeViewEventDispatchTest(unittest.IsolatedAsyncioTestCase):
    def _bridge(self):
        plugin = SimpleNamespace(pages={})
        bridge = Bridge(plugin, transport=ClientTransport())
        plugin.views = Views(bridge)
        bridge._handshake_state = "ready"
        bridge.asyncio_loop = asyncio.get_running_loop()
        bridge.message_queue = asyncio.Queue(maxsize=16)
        return bridge, plugin

    def _frames(self, bridge, *view_events):
        return [
            Envelope(
                type="ide.view.event",
                plugin_id=bridge.plugin_id,
                session_id=bridge.session_id,
                generation=bridge.generation,
                sequence=index,
                payload=payload,
            ).model_dump_json(by_alias=True)
            for index, payload in enumerate(view_events, start=1)
        ]

    @staticmethod
    def _event(event, number):
        return {
            "instance": {"instanceId": "i1"},
            "componentId": "root",
            "event": event,
            "payload": {"n": number},
        }

    async def test_async_handler_is_awaited_before_the_next_frame(self):
        bridge, plugin = self._bridge()
        view = plugin.views.create("panel", instance_id="i1")
        received = []

        async def first(payload):
            await asyncio.sleep(0)
            received.append(("first", payload))

        def second(payload):
            received.append(("second", payload))

        view.on_event("root", "async", first)
        view.on_event("root", "sync", second)
        client = FakeClient(
            self._frames(
                bridge,
                self._event("async", 1),
                self._event("sync", 2),
            )
        )

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            await bridge.handler(client)

        self.assertEqual(
            received,
            [("first", {"n": 1}), ("second", {"n": 2})],
        )
        self.assertFalse(
            [
                warning
                for warning in caught
                if issubclass(warning.category, RuntimeWarning)
                and "never awaited" in str(warning.message)
            ]
        )

    async def test_async_handler_error_is_reported_and_later_frames_run(self):
        bridge, plugin = self._bridge()
        view = plugin.views.create("panel", instance_id="i1")
        received = []

        async def boom(payload):
            await asyncio.sleep(0)
            raise RuntimeError("async handler boom")

        def later(payload):
            received.append(payload)

        view.on_event("root", "async", boom)
        view.on_event("root", "later", later)
        client = FakeClient(
            self._frames(
                bridge,
                self._event("async", 1),
                self._event("later", 2),
            )
        )

        await bridge.handler(client)
        await _wait_until(lambda: bridge.message_queue.qsize() >= 1)

        self.assertEqual(received, [{"n": 2}])
        reports = []
        while not bridge.message_queue.empty():
            _, envelope = bridge.message_queue.get_nowait()
            if envelope.type == "sdk.runtime.report_error":
                reports.append(envelope)
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0].payload["source"], "ide.view.event")
        self.assertIn("async handler boom", reports[0].payload["message"])
        self.assertIn("async handler boom", reports[0].payload["traceback"])


if __name__ == "__main__":
    unittest.main()
