import asyncio
import unittest
from types import SimpleNamespace

from pyrite_sdk.core.bridge import Bridge
from pyrite_sdk.models.schema import Envelope, request
from tests.fakes import ClientTransport, FakeClient


class _Disposable:
    def __init__(self):
        self.calls = 0

    def dispose_all(self):
        self.calls += 1


async def _wait_until(predicate, timeout=1.0):
    async with asyncio.timeout(timeout):
        while not predicate():
            await asyncio.sleep(0)


class BridgeHealthRecoveryTest(unittest.IsolatedAsyncioTestCase):
    def _bridge(self, plugin=None):
        return Bridge(
            plugin or SimpleNamespace(pages={}),
            transport=ClientTransport(),
        )

    async def test_health_ping_returns_runtime_counts(self):
        bridge = self._bridge()
        bridge._handshake_state = "ready"
        bridge.asyncio_loop = asyncio.get_running_loop()
        bridge.message_queue = asyncio.Queue(maxsize=8)
        ping = Envelope(
            type="ide.health.ping",
            plugin_id=bridge.plugin_id,
            session_id=bridge.session_id,
            generation=bridge.generation,
            sequence=1,
            payload={},
        )
        client = FakeClient([ping.model_dump_json(by_alias=True)])

        await bridge.handler(client)
        await asyncio.sleep(0)

        _, response = bridge.message_queue.get_nowait()
        self.assertEqual(response.type, "sdk.health.pong")
        self.assertEqual(response.reply_to, ping.request_id)
        self.assertEqual(response.payload["status"], "ok")
        self.assertIn("activeRequestTasks", response.payload)
        self.assertIn("pendingResponses", response.payload)

    async def test_unhandled_request_task_error_is_reported(self):
        bridge = self._bridge()
        bridge.asyncio_loop = asyncio.get_running_loop()
        bridge.message_queue = asyncio.Queue(maxsize=8)

        async def fail():
            raise RuntimeError("task boom")

        envelope = request("ide.fixture.task")
        bridge._start_request_task(envelope, fail())
        await _wait_until(lambda: bridge.message_queue.qsize() == 1)

        _, report = bridge.message_queue.get_nowait()
        self.assertEqual(report.type, "sdk.runtime.report_error")
        self.assertIn("task boom", report.payload["message"])
        self.assertEqual(report.payload["source"], "ide.fixture.task")

    async def test_dispose_clears_plugin_apis_and_pending_callbacks(self):
        events = _Disposable()
        commands = _Disposable()
        views = _Disposable()
        plugin = SimpleNamespace(
            pages={},
            events=events,
            commands=commands,
            views=views,
            on_dispose=lambda: None,
        )
        bridge = self._bridge(plugin)
        bridge.asyncio_loop = asyncio.get_running_loop()
        bridge.message_queue = asyncio.Queue(maxsize=8)
        bridge.callbacks["pending"] = lambda **_: None
        bridge._pending_responses = 1
        envelope = request("ide.lifecycle.hook", {"hook": "dispose"})
        client = FakeClient()

        await bridge._run_lifecycle_request(envelope, client)

        self.assertTrue(bridge._disposed)
        self.assertEqual(events.calls, 1)
        self.assertEqual(commands.calls, 1)
        self.assertEqual(views.calls, 1)
        self.assertEqual(bridge.callbacks, {})
        self.assertEqual(bridge._pending_responses, 0)


if __name__ == "__main__":
    unittest.main()
