import asyncio
import os
import sys
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from pyrite_sdk.core.bridge import Bridge
from pyrite_sdk.core.dart_bridge_transport import (
    DART_CHANNEL_LABEL_ENV,
    DART_PORT_ENV,
    DART_SESSION_TOKEN_ENV,
    DART_SESSION_TOKEN_LABEL,
    DartBridgeTransport,
)
from pyrite_sdk.core.transport import TransportState
from pyrite_sdk.models.schema import Envelope


class FakeDartBridge:
    def __init__(self):
        self.handlers = {}
        self.restart_handlers = []
        self.sent = []

    def set_enqueue_handler_func(self, port, handler):
        self.handlers[port] = handler

    def send_bytes(self, port, payload):
        self.sent.append((port, bytes(payload)))

    def add_session_restart_handler(self, handler):
        self.restart_handlers.append(handler)

    def deliver(self, port, payload):
        handler = self.handlers.get(port)
        if handler is None:
            raise RuntimeError(f"No handler for port {port}")
        handler(payload)

    def restart(self, ports):
        for handler in list(self.restart_handlers):
            handler(ports)


class FailingUnregisterDartBridge(FakeDartBridge):
    def set_enqueue_handler_func(self, port, handler):
        if handler is None:
            raise RuntimeError("native unregister failed")
        super().set_enqueue_handler_func(port, handler)


class FailingSendDartBridge(FakeDartBridge):
    def __init__(self):
        super().__init__()
        self.fail_sends = False

    def send_bytes(self, port, payload):
        if self.fail_sends:
            raise OSError("native send failed")
        super().send_bytes(port, payload)


async def _wait_until(predicate, timeout=1.0):
    async with asyncio.timeout(timeout):
        while not predicate():
            await asyncio.sleep(0)


class DartBridgeTransportTest(unittest.IsolatedAsyncioTestCase):
    async def test_bridge_completes_protocol_handshake_over_dart_transport(self):
        native_bridge = FakeDartBridge()
        transport = DartBridgeTransport(
            100,
            "plugin.handshake",
            bridge_module=native_bridge,
        )
        bridge = Bridge(SimpleNamespace(pages={}), transport=transport)
        main_task = asyncio.create_task(bridge.main())
        await _wait_until(lambda: native_bridge.handlers.get(100) is not None)

        native_bridge.deliver(
            100,
            Envelope(
                type="ide.initialize",
                sequence=1,
                payload={
                    "protocolVersion": 1,
                    "pluginId": "standalone",
                    "capabilities": ["sdk.v1"],
                },
            )
            .model_dump_json(by_alias=True)
            .encode(),
        )
        await _wait_until(lambda: len(native_bridge.sent) == 1)
        sdk_initialize = Envelope.model_validate_json(native_bridge.sent[0][1])
        native_bridge.deliver(
            100,
            Envelope(
                type="ide.initialized",
                sequence=2,
                reply_to=sdk_initialize.request_id,
                payload={
                    "protocolVersion": 1,
                    "capabilities": ["sdk.v1"],
                },
            )
            .model_dump_json(by_alias=True)
            .encode(),
        )
        await _wait_until(lambda: len(native_bridge.sent) == 2)

        sdk_ready = Envelope.model_validate_json(native_bridge.sent[1][1])
        self.assertEqual(sdk_initialize.type, "sdk.initialize")
        self.assertEqual(sdk_ready.type, "sdk.ready")
        bridge.stop()
        await main_task

    async def test_round_trip_sizes_and_native_callback_thread_handoff(self):
        bridge = FakeDartBridge()
        transport = DartBridgeTransport(
            101,
            "plugin.payloads",
            bridge_module=bridge,
        )
        received = []
        handler_threads = []
        callback_thread = None

        async def handler(client):
            async for message in transport.messages(client):
                handler_threads.append(threading.get_ident())
                received.append(message)
                await transport.send(client, message)

        await transport.start(handler)
        sizes = [0, 1, 1024, 64 * 1024, 1024 * 1024]
        for size in sizes:
            payload = bytes(index & 0xFF for index in range(size))

            def deliver():
                nonlocal callback_thread
                callback_thread = threading.get_ident()
                bridge.deliver(101, payload)

            thread = threading.Thread(target=deliver)
            thread.start()
            thread.join()

        await _wait_until(lambda: len(received) == len(sizes))

        self.assertEqual([len(message) for message in received], sizes)
        self.assertEqual([len(payload) for _, payload in bridge.sent], sizes)
        self.assertTrue(
            all(thread_id != callback_thread for thread_id in handler_threads)
        )
        transport.close()
        await transport.wait_closed()

    async def test_three_channels_do_not_cross_route_interleaved_messages(self):
        bridge = FakeDartBridge()
        transports = [
            DartBridgeTransport(
                200 + index,
                f"plugin.{index}",
                bridge_module=bridge,
            )
            for index in range(3)
        ]
        received = [[] for _ in transports]

        def make_handler(index):
            async def handler(client):
                async for message in transports[index].messages(client):
                    received[index].append(message)

            return handler

        for index, transport in enumerate(transports):
            await transport.start(make_handler(index))

        bridge.deliver(202, b"c1")
        bridge.deliver(200, b"a")
        bridge.deliver(201, b"b")
        bridge.deliver(202, b"c2")
        await _wait_until(lambda: sum(map(len, received)) == 4)

        self.assertEqual(received, [[b"a"], [b"b"], [b"c1", b"c2"]])
        self.assertEqual(len(bridge.restart_handlers), 1)
        for transport in transports:
            transport.close()
        await asyncio.gather(*(transport.wait_closed() for transport in transports))

    async def test_session_restart_rebinds_the_channel_port(self):
        bridge = FakeDartBridge()
        transport = DartBridgeTransport(
            301,
            "plugin.restart",
            bridge_module=bridge,
        )
        received = []

        async def handler(client):
            async for message in transport.messages(client):
                received.append(message)
                await transport.send(client, b"reply")

        await transport.start(handler)
        bridge.restart({"plugin.restart": 302})
        await _wait_until(lambda: transport.port == 302)
        bridge.deliver(302, b"request")
        await _wait_until(lambda: received == [b"request"])

        self.assertIsNone(bridge.handlers[301])
        self.assertEqual(bridge.sent, [(302, b"reply")])
        transport.close()
        await transport.wait_closed()

    async def test_new_dart_session_disposes_old_bridge_before_reuse(self):
        native_bridge = FakeDartBridge()
        old_transport = DartBridgeTransport(
            303,
            "plugin.session",
            bridge_module=native_bridge,
            dart_session_token=11,
        )
        old_bridge = Bridge(SimpleNamespace(pages={}), transport=old_transport)
        old_main = asyncio.create_task(old_bridge.main())
        await _wait_until(lambda: native_bridge.handlers.get(303) is not None)

        native_bridge.restart({DART_SESSION_TOKEN_LABEL: 11})
        await asyncio.sleep(0)
        self.assertEqual(old_transport.state, TransportState.READY)

        native_bridge.restart({DART_SESSION_TOKEN_LABEL: 12})
        await asyncio.wait_for(old_main, timeout=1)
        self.assertEqual(old_transport.state, TransportState.CLOSED)
        self.assertIsNone(native_bridge.handlers[303])

        new_transport = DartBridgeTransport(
            304,
            "plugin.session",
            bridge_module=native_bridge,
            dart_session_token=12,
        )
        new_bridge = Bridge(SimpleNamespace(pages={}), transport=new_transport)
        new_main = asyncio.create_task(new_bridge.main())
        await _wait_until(lambda: native_bridge.handlers.get(304) is not None)

        native_bridge.deliver(
            304,
            Envelope(
                type="ide.initialize",
                session_id="new-session",
                generation=2,
                sequence=1,
                payload={
                    "protocolVersion": 1,
                    "pluginId": "standalone",
                    "capabilities": ["sdk.v1"],
                },
            )
            .model_dump_json(by_alias=True)
            .encode(),
        )
        await _wait_until(lambda: len(native_bridge.sent) == 1)
        sdk_initialize = Envelope.model_validate_json(native_bridge.sent[0][1])
        native_bridge.deliver(
            304,
            Envelope(
                type="ide.initialized",
                session_id="new-session",
                generation=2,
                sequence=2,
                reply_to=sdk_initialize.request_id,
                payload={
                    "protocolVersion": 1,
                    "capabilities": ["sdk.v1"],
                },
            )
            .model_dump_json(by_alias=True)
            .encode(),
        )
        await _wait_until(lambda: len(native_bridge.sent) == 2)
        self.assertEqual(
            Envelope.model_validate_json(native_bridge.sent[1][1]).type,
            "sdk.ready",
        )

        new_bridge.stop()
        await new_main

    async def test_queue_is_bounded_and_overflow_fails_the_consumer(self):
        bridge = FakeDartBridge()
        transport = DartBridgeTransport(
            401,
            "plugin.overflow",
            queue_size=1,
            bridge_module=bridge,
        )
        release = asyncio.Event()
        failures = []

        async def handler(client):
            await release.wait()
            try:
                async for _ in transport.messages(client):
                    pass
            except RuntimeError as error:
                failures.append(error)

        await transport.start(handler)
        bridge.deliver(401, b"first")
        bridge.deliver(401, b"second")
        await _wait_until(lambda: transport.state == TransportState.FAILED)
        release.set()
        await _wait_until(lambda: len(failures) == 1)

        self.assertLessEqual(transport._queue.qsize(), 1)
        transport.close()
        await transport.wait_closed()

    async def test_one_hundred_channels_unregister_without_callback_growth(self):
        bridge = FakeDartBridge()
        for index in range(100):
            transport = DartBridgeTransport(
                500 + index,
                f"plugin.dispose.{index}",
                bridge_module=bridge,
            )

            async def handler(client, current=transport):
                async for _ in current.messages(client):
                    pass

            await transport.start(handler)
            transport.close()
            await transport.wait_closed()

        self.assertEqual(len(bridge.restart_handlers), 1)
        self.assertTrue(all(handler is None for handler in bridge.handlers.values()))

    async def test_handler_failure_closes_and_unregisters_the_channel(self):
        bridge = FakeDartBridge()
        transport = DartBridgeTransport(
            650,
            "plugin.handler.failure",
            bridge_module=bridge,
        )

        async def handler(_client):
            raise RuntimeError("handler failed")

        await transport.start(handler)
        with self.assertRaisesRegex(RuntimeError, "handler failed"):
            await transport.wait_closed()

        self.assertEqual(transport.state, TransportState.CLOSED)
        self.assertIsNone(bridge.handlers[650])

    async def test_start_rollback_unregisters_a_partially_created_channel(self):
        bridge = FakeDartBridge()
        transport = DartBridgeTransport(
            651,
            "plugin.start.rollback",
            bridge_module=bridge,
        )

        with self.assertRaises(TypeError):
            await transport.start(lambda _client: None)  # type: ignore[arg-type]

        self.assertEqual(transport.state, TransportState.FAILED)
        self.assertIsNone(bridge.handlers[651])

    async def test_close_completes_when_native_unregister_fails(self):
        bridge = FailingUnregisterDartBridge()
        transport = DartBridgeTransport(
            652,
            "plugin.unregister.failure",
            bridge_module=bridge,
        )

        async def handler(client):
            async for _ in transport.messages(client):
                pass

        await transport.start(handler)
        transport.close()
        await transport.wait_closed()

        self.assertEqual(transport.state, TransportState.CLOSED)

    async def test_bridge_main_exits_when_transport_closes_directly(self):
        native_bridge = FakeDartBridge()
        transport = DartBridgeTransport(
            653,
            "plugin.direct.close",
            bridge_module=native_bridge,
        )
        bridge = Bridge(SimpleNamespace(pages={}), transport=transport)
        main_task = asyncio.create_task(bridge.main())
        await _wait_until(lambda: native_bridge.handlers.get(653) is not None)

        transport.close()
        await asyncio.wait_for(main_task, timeout=1)

        self.assertEqual(transport.state, TransportState.CLOSED)

    async def test_native_send_failure_fails_pending_bridge_requests(self):
        native_bridge = FailingSendDartBridge()
        transport = DartBridgeTransport(
            654,
            "plugin.send.failure",
            bridge_module=native_bridge,
        )
        bridge = Bridge(SimpleNamespace(pages={}), transport=transport)
        main_task = asyncio.create_task(bridge.main())
        await _wait_until(lambda: native_bridge.handlers.get(654) is not None)

        native_bridge.deliver(
            654,
            Envelope(
                type="ide.initialize",
                sequence=1,
                payload={
                    "protocolVersion": 1,
                    "pluginId": "standalone",
                    "capabilities": ["sdk.v1"],
                },
            )
            .model_dump_json(by_alias=True)
            .encode(),
        )
        await _wait_until(lambda: len(native_bridge.sent) == 1)
        sdk_initialize = Envelope.model_validate_json(native_bridge.sent[0][1])
        native_bridge.deliver(
            654,
            Envelope(
                type="ide.initialized",
                sequence=2,
                reply_to=sdk_initialize.request_id,
                payload={
                    "protocolVersion": 1,
                    "capabilities": ["sdk.v1"],
                },
            )
            .model_dump_json(by_alias=True)
            .encode(),
        )
        await _wait_until(lambda: len(native_bridge.sent) == 2)

        errors = []
        native_bridge.fail_sends = True
        bridge.push_wait_response(
            Envelope(type="sdk.fixture", payload={}),
            callback=lambda **data: errors.append(data.get("error")),
        )

        await asyncio.wait_for(main_task, timeout=1)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], ConnectionError)
        self.assertEqual(bridge.callbacks, {})
        self.assertEqual(bridge._pending_responses, 0)

    def test_environment_requires_current_native_context(self):
        bridge = FakeDartBridge()
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, DART_PORT_ENV):
                DartBridgeTransport.from_environment(bridge_module=bridge)
        with patch.dict(
            os.environ,
            {DART_PORT_ENV: "10"},
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, DART_CHANNEL_LABEL_ENV):
                DartBridgeTransport.from_environment(bridge_module=bridge)
        with patch.dict(
            os.environ,
            {
                DART_PORT_ENV: "10",
                DART_CHANNEL_LABEL_ENV: "plugin.missing-token",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, DART_SESSION_TOKEN_ENV):
                DartBridgeTransport.from_environment(bridge_module=bridge)

        for invalid_port in ("not-an-integer", "0", "-1"):
            with (
                self.subTest(port=invalid_port),
                patch.dict(
                    os.environ,
                    {
                        DART_PORT_ENV: invalid_port,
                        DART_CHANNEL_LABEL_ENV: "plugin.invalid",
                        DART_SESSION_TOKEN_ENV: "1",
                    },
                    clear=True,
                ),
            ):
                with self.assertRaises((RuntimeError, ValueError)):
                    DartBridgeTransport.from_environment(bridge_module=bridge)

    def test_bridge_defaults_to_dart_transport_and_rejects_tcp_startup(self):
        native_bridge = FakeDartBridge()
        plugin_root = os.path.abspath("test-plugin")
        with (
            patch.dict(
                os.environ,
                {
                    DART_PORT_ENV: "700",
                    DART_CHANNEL_LABEL_ENV: "plugin.default",
                    DART_SESSION_TOKEN_ENV: "123",
                    "PYRITE_IDE_PLUGIN_ID": "default-plugin",
                    "PYRITE_IDE_PLUGIN_SESSION_ID": "default-session",
                    "PYRITE_IDE_PLUGIN_GENERATION": "1",
                    "PYRITE_IDE_PLUGIN_DIR": plugin_root,
                    "PYRITE_IDE_PLUGIN_DATA_DIR": os.path.join(
                        plugin_root,
                        "data",
                    ),
                    "PYRITE_IDE_PLUGIN_CACHE_DIR": os.path.join(
                        plugin_root,
                        "cache",
                    ),
                    "PYRITE_IDE_PLUGIN_TEMP_DIR": os.path.join(
                        plugin_root,
                        "temp",
                    ),
                    "PYRITE_IDE_PLUGIN_CAPABILITIES": '["sdk.v1", "native.views"]',
                },
                clear=True,
            ),
            patch.dict(sys.modules, {"dart_bridge": native_bridge}),
        ):
            bridge = Bridge(SimpleNamespace())

        self.assertIsInstance(bridge.transport, DartBridgeTransport)
        self.assertEqual(bridge.transport.port, 700)
        self.assertEqual(bridge.transport.dart_session_token, 123)

        with patch.dict(
            os.environ,
            {
                "PYRITE_IDE_PLUGIN_PORT": "700",
                DART_PORT_ENV: "701",
                DART_CHANNEL_LABEL_ENV: "plugin.legacy",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "no longer supported"):
                Bridge(SimpleNamespace(pages={}))


if __name__ == "__main__":
    unittest.main()
