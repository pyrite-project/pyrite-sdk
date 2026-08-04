import asyncio
import unittest
from pathlib import Path
from types import SimpleNamespace

from pyrite_sdk.core.bridge import Bridge
from pyrite_sdk.core.transport import TransportClosedError
from pyrite_sdk.models.consts import PathScope
from pyrite_sdk.models.schema import request
from tests.fakes import ClientTransport


async def _wait_until(predicate, timeout=1.0):
    async with asyncio.timeout(timeout):
        while not predicate():
            await asyncio.sleep(0)


class BridgePendingResponseTest(unittest.IsolatedAsyncioTestCase):
    def _bridge(self) -> Bridge:
        return Bridge(
            SimpleNamespace(pages={}),
            transport=ClientTransport(),
        )

    async def test_closed_loop_fails_request_without_retaining_callback(self):
        bridge = self._bridge()
        errors = []

        queued = bridge.push_wait_response(
            request("sdk.fixture"),
            callback=lambda **data: errors.append(data.get("error")),
        )

        self.assertFalse(queued)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], TransportClosedError)
        self.assertEqual(bridge.callbacks, {})
        self.assertEqual(bridge._pending_responses, 0)

    async def test_full_queue_fails_only_the_dropped_request(self):
        bridge = self._bridge()
        bridge.asyncio_loop = asyncio.get_running_loop()
        bridge.message_queue = asyncio.Queue(maxsize=1)
        bridge.message_queue.put_nowait([None, request("sdk.blocker")])
        errors = []

        bridge.push_wait_response(
            request("sdk.dropped"),
            callback=lambda **data: errors.append(data.get("error")),
        )
        await _wait_until(lambda: len(errors) == 1)

        self.assertIsInstance(errors[0], RuntimeError)
        self.assertIn("queue is full", str(errors[0]))
        self.assertEqual(bridge.callbacks, {})
        self.assertEqual(bridge._pending_responses, 0)

    async def test_same_scope_path_requests_correlate_by_request_id(self):
        bridge = self._bridge()
        bridge.asyncio_loop = asyncio.get_running_loop()
        bridge.message_queue = asyncio.Queue(maxsize=4)

        first = asyncio.create_task(
            asyncio.to_thread(bridge.request_path, PathScope.PLUGIN, 1.0)
        )
        second = asyncio.create_task(
            asyncio.to_thread(bridge.request_path, PathScope.PLUGIN, 1.0)
        )
        await _wait_until(lambda: bridge.message_queue.qsize() == 2)

        queued = []
        while not bridge.message_queue.empty():
            _, envelope = bridge.message_queue.get_nowait()
            queued.append(envelope)
            bridge.message_queue.task_done()
        self.assertNotEqual(queued[0].request_id, queued[1].request_id)

        bridge._complete_pending_response(
            queued[1].request_id,
            data={"scope": "plugin", "path": "host/second"},
        )
        bridge._complete_pending_response(
            queued[0].request_id,
            data={"scope": "plugin", "path": "host/first"},
        )

        results = await asyncio.gather(first, second)
        self.assertEqual(
            set(results),
            {Path("host/first"), Path("host/second")},
        )
        self.assertEqual(bridge.callbacks, {})
        self.assertEqual(bridge._pending_responses, 0)

    async def test_path_timeout_removes_pending_callback(self):
        bridge = self._bridge()
        bridge.asyncio_loop = asyncio.get_running_loop()
        bridge.message_queue = asyncio.Queue(maxsize=1)

        with self.assertRaisesRegex(TimeoutError, "plugin path"):
            await asyncio.to_thread(
                bridge.request_path,
                PathScope.PLUGIN,
                0.01,
            )

        self.assertEqual(bridge.callbacks, {})
        self.assertEqual(bridge._pending_responses, 0)

    async def test_active_request_task_can_be_cancelled_by_request_id(self):
        bridge = self._bridge()
        started = asyncio.Event()
        cancelled = asyncio.Event()

        async def operation():
            started.set()
            try:
                await asyncio.Future()
            finally:
                cancelled.set()

        envelope = request("ide.fixture.slow")
        bridge._start_request_task(envelope, operation())
        await started.wait()

        self.assertTrue(bridge._cancel_request_task(envelope.request_id))
        await cancelled.wait()
        await asyncio.sleep(0)
        self.assertNotIn(envelope.request_id, bridge._request_tasks)


if __name__ == "__main__":
    unittest.main()
