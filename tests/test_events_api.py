import asyncio
import unittest

from pyrite_sdk.api.events import PluginEventBus


class FakeBridge:
    def __init__(self):
        self.calls = []
        self.logs = []
        self.errors = []

    def push_wait_response(self, envelope, callback=None, client=None):
        self.calls.append((envelope, callback, client))

    def _log_internal(self, *args):
        self.logs.append(" ".join(str(a) for a in args))

    def report_error(self, message, **details):
        self.errors.append((message, details))


class EventsApiTest(unittest.TestCase):
    def setUp(self):
        self.bridge = FakeBridge()
        self.bus = PluginEventBus(self.bridge)

    def last_request(self):
        envelope, callback, _ = self.bridge.calls[-1]
        return envelope, callback

    def test_subscribe_sends_topic_filter_and_delivery(self):
        self.bus.subscribe(
            "editor.document.changed",
            lambda event: None,
            filter={"language": "python"},
            delivery="debounce",
            debounce_ms=120,
        )
        envelope, _ = self.last_request()
        self.assertEqual(envelope.type, "sdk.events.subscribe")
        payload = envelope.payload
        self.assertEqual(payload["topic"], "editor.document.changed")
        self.assertEqual(payload["filter"], {"language": "python"})
        self.assertEqual(payload["delivery"], {"mode": "debounce", "debounceMs": 120})
        self.assertIn("subscriptionId", payload)

    def test_subscribe_returns_live_subscription(self):
        subscription = self.bus.subscribe("view.opened", lambda event: None)
        self.assertFalse(subscription.disposed)
        self.assertEqual(subscription.topic, "view.opened")

    def test_dispose_sends_unsubscribe_and_marks_disposed(self):
        subscription = self.bus.subscribe("view.opened", lambda event: None)
        self.bridge.calls.clear()
        subscription.dispose()
        self.assertTrue(subscription.disposed)
        envelope, _ = self.last_request()
        self.assertEqual(envelope.type, "sdk.events.unsubscribe")
        self.assertEqual(
            envelope.payload["subscriptionId"], subscription.id
        )

    def test_dispose_all_releases_without_notifying_host(self):
        self.bus.subscribe("view.opened", lambda event: None)
        self.bus.subscribe("view.closed", lambda event: None)
        self.bridge.calls.clear()
        self.bus.dispose_all()
        self.assertEqual(self.bridge.calls, [])

    def test_dispatch_invokes_handler_per_event(self):
        received = []
        subscription = self.bus.subscribe(
            "view.opened", lambda event: received.append(event)
        )
        asyncio.run(
            self.bus.dispatch(
                subscription.id, "view.opened", [{"a": 1}, {"a": 2}]
            )
        )
        self.assertEqual(received, [{"a": 1}, {"a": 2}])

    def test_dispatch_awaits_async_handlers(self):
        received = []

        async def handler(event):
            received.append(event)

        subscription = self.bus.subscribe("view.opened", handler)
        asyncio.run(
            self.bus.dispatch(subscription.id, "view.opened", [{"x": 1}])
        )
        self.assertEqual(received, [{"x": 1}])

    def test_handler_exception_is_isolated(self):
        received = []

        def bad(event):
            raise ValueError("boom")

        good_sub = None

        def good(event):
            received.append(event)

        bad_sub = self.bus.subscribe("view.opened", bad)
        good_sub = self.bus.subscribe("view.closed", good)

        # A raising handler must not propagate out of dispatch.
        asyncio.run(self.bus.dispatch(bad_sub.id, "view.opened", [{"n": 1}]))
        asyncio.run(self.bus.dispatch(good_sub.id, "view.closed", [{"n": 2}]))

        self.assertEqual(received, [{"n": 2}])
        self.assertTrue(any("raised" in log for log in self.bridge.logs))
        self.assertEqual(len(self.bridge.errors), 1)
        self.assertEqual(self.bridge.errors[0][1]["source"], "event:view.opened")

    def test_dispatch_to_unknown_subscription_is_ignored(self):
        # No handler registered; must not raise.
        asyncio.run(self.bus.dispatch("nope", "view.opened", [{"n": 1}]))

    def test_dispatch_skips_disposed_subscription(self):
        received = []
        subscription = self.bus.subscribe(
            "view.opened", lambda event: received.append(event)
        )
        subscription.dispose()
        asyncio.run(
            self.bus.dispatch(subscription.id, "view.opened", [{"n": 1}])
        )
        self.assertEqual(received, [])

    def test_error_response_drops_subscription_locally(self):
        subscription = self.bus.subscribe("view.opened", lambda event: None)
        _, callback = self.last_request()
        callback(error=RuntimeError("denied"))
        # After a host rejection the subscription is no longer tracked.
        asyncio.run(
            self.bus.dispatch(subscription.id, "view.opened", [{"n": 1}])
        )
        # Dispatch is a no-op because the subscription was removed.
        self.assertTrue(subscription.disposed)


if __name__ == "__main__":
    unittest.main()
