import asyncio
import io
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from types import SimpleNamespace

from pyrite_sdk.core.bridge import Bridge, BridgeOutputRouter, MAX_LOG_BATCH_BYTES
from tests.fakes import ClientTransport


class BridgeOutputRouterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.stdout_router = BridgeOutputRouter("stdout", io.StringIO())
        self.stderr_router = BridgeOutputRouter("stderr", io.StringIO())
        with BridgeOutputRouter._route_lock:
            self.saved_stdout_router = BridgeOutputRouter._stdout
            self.saved_stderr_router = BridgeOutputRouter._stderr
            self.saved_routes = dict(BridgeOutputRouter._routes)
            BridgeOutputRouter._stdout = self.stdout_router
            BridgeOutputRouter._stderr = self.stderr_router
            BridgeOutputRouter._routes.clear()
        BridgeOutputRouter._patch_threading()

    def tearDown(self) -> None:
        with BridgeOutputRouter._route_lock:
            BridgeOutputRouter._routes.clear()
            BridgeOutputRouter._routes.update(self.saved_routes)
            BridgeOutputRouter._stdout = self.saved_stdout_router
            BridgeOutputRouter._stderr = self.saved_stderr_router

    def make_bridge(self) -> Bridge:
        return Bridge(
            SimpleNamespace(pages={}),
            transport=ClientTransport(),
        )

    @staticmethod
    def activate_bridge(bridge: Bridge) -> None:
        bridge._output_redirected = True
        BridgeOutputRouter.register_current_thread(bridge)

    def test_thread_exit_removes_route_and_partial_buffers(self) -> None:
        bridge = self.make_bridge()
        output = []
        bridge.emit_output = lambda stream, text: output.append((stream, text))
        self.activate_bridge(bridge)
        child_thread_ids = []
        child_bridges = []

        def write_partial_line() -> None:
            child_thread_ids.append(threading.get_ident())
            child_bridges.append(BridgeOutputRouter.current_bridge())
            self.stdout_router.write("partial stdout")
            self.stderr_router.write("partial stderr")

        worker = threading.Thread(target=write_partial_line)
        worker.start()
        worker.join(timeout=2)

        self.assertFalse(worker.is_alive())
        self.assertEqual(child_bridges, [bridge])
        child_thread_id = child_thread_ids[0]
        self.assertNotIn(child_thread_id, BridgeOutputRouter._routes)
        self.assertNotIn(child_thread_id, self.stdout_router._buffers)
        self.assertNotIn(child_thread_id, self.stderr_router._buffers)
        self.assertEqual(output, [])

    def test_rebinding_thread_discards_previous_bridge_buffer(self) -> None:
        first_bridge = self.make_bridge()
        second_bridge = self.make_bridge()
        first_output = []
        second_output = []
        first_bridge.emit_output = (
            lambda stream, text: first_output.append((stream, text))
        )
        second_bridge.emit_output = (
            lambda stream, text: second_output.append((stream, text))
        )
        self.activate_bridge(first_bridge)
        self.stdout_router.write("stale partial")

        self.activate_bridge(second_bridge)
        self.stdout_router.write("current\n")

        self.assertEqual(first_output, [])
        self.assertEqual(second_output, [("stdout", "current")])
        self.assertEqual(self.stdout_router._buffers[threading.get_ident()], "")

    def test_thread_subclass_inherits_and_releases_route(self) -> None:
        bridge = self.make_bridge()
        output = []
        bridge.emit_output = lambda stream, text: output.append((stream, text))
        self.activate_bridge(bridge)
        child_thread_ids = []
        child_bridges = []

        class PluginThread(threading.Thread):
            def run(self) -> None:
                child_thread_ids.append(threading.get_ident())
                child_bridges.append(BridgeOutputRouter.current_bridge())
                self_router.write("subclass output\n")

        self_router = self.stdout_router
        worker = PluginThread()
        worker.start()
        worker.join(timeout=2)

        self.assertFalse(worker.is_alive())
        self.assertEqual(child_bridges, [bridge])
        self.assertEqual(output, [("stdout", "subclass output")])
        self.assertNotIn(child_thread_ids[0], BridgeOutputRouter._routes)
        self.assertNotIn(child_thread_ids[0], self.stdout_router._buffers)

    def test_stop_removes_routes_before_late_thread_output(self) -> None:
        bridge = self.make_bridge()
        output = []
        bridge.emit_output = lambda stream, text: output.append((stream, text))
        self.activate_bridge(bridge)
        child_registered = threading.Event()
        allow_late_output = threading.Event()
        child_thread_ids = []

        def keep_writing_after_stop() -> None:
            child_thread_ids.append(threading.get_ident())
            self.stdout_router.write("partial")
            child_registered.set()
            allow_late_output.wait(timeout=2)
            self.stdout_router.write("late\n")

        worker = threading.Thread(target=keep_writing_after_stop)
        worker.start()
        self.assertTrue(child_registered.wait(timeout=2))

        try:
            bridge.stop()
            child_thread_id = child_thread_ids[0]
            self.assertNotIn(bridge, BridgeOutputRouter._routes.values())
            self.assertNotIn(child_thread_id, self.stdout_router._buffers)
            self.assertFalse(bridge._output_redirected)
        finally:
            allow_late_output.set()
            worker.join(timeout=2)

        self.assertFalse(worker.is_alive())
        self.assertEqual(output, [])
        self.assertNotIn(child_thread_ids[0], self.stdout_router._buffers)

    def test_main_teardown_removes_current_thread_route(self) -> None:
        bridge = self.make_bridge()
        self.activate_bridge(bridge)
        thread_id = threading.get_ident()
        self.stdout_router.write("partial")

        asyncio.run(bridge.main())

        self.assertNotIn(thread_id, BridgeOutputRouter._routes)
        self.assertNotIn(thread_id, self.stdout_router._buffers)
        self.assertFalse(bridge._output_redirected)

    def test_output_chunks_stay_within_the_utf8_batch_budget(self) -> None:
        text = "界" * (MAX_LOG_BATCH_BYTES // 2)
        chunks = Bridge._chunk_output_text(text)

        self.assertGreater(len(chunks), 1)
        self.assertEqual("".join(chunks), text)
        self.assertTrue(
            all(len(chunk.encode("utf-8")) <= MAX_LOG_BATCH_BYTES for chunk in chunks)
        )

    def test_router_exposes_the_text_stream_interface(self) -> None:
        router = BridgeOutputRouter("stdout", io.StringIO())

        self.assertIs(router.buffer, router.buffer)
        self.assertTrue(callable(router.buffer.write))
        self.assertTrue(callable(router.buffer.flush))
        self.assertTrue(router.writable())
        self.assertIsNone(router.errors)
        self.assertFalse(router.closed)

    def test_binary_buffer_writes_are_decoded_and_routed(self) -> None:
        bridge = self.make_bridge()
        output = []
        bridge.emit_output = lambda stream, text: output.append((stream, text))
        self.activate_bridge(bridge)
        original = io.StringIO()
        router = BridgeOutputRouter("stdout", original)
        payload = "λog line\n".encode()

        written = router.buffer.write(payload)
        router.buffer.flush()

        self.assertEqual(written, len(payload))
        self.assertEqual(original.getvalue(), "λog line\n")
        self.assertEqual(output, [("stdout", "λog line")])

    def test_binary_buffer_replaces_invalid_bytes(self) -> None:
        bridge = self.make_bridge()
        output = []
        bridge.emit_output = lambda stream, text: output.append((stream, text))
        self.activate_bridge(bridge)
        original = io.StringIO()
        router = BridgeOutputRouter("stdout", original)

        written = router.buffer.write(b"bad byte: \xff\n")
        router.buffer.flush()

        self.assertEqual(written, len(b"bad byte: \xff\n"))
        self.assertEqual(original.getvalue(), "bad byte: �\n")
        self.assertEqual(output, [("stdout", "bad byte: �")])

    def test_binary_buffer_keeps_characters_split_across_writes(self) -> None:
        bridge = self.make_bridge()
        output = []
        bridge.emit_output = lambda stream, text: output.append((stream, text))
        self.activate_bridge(bridge)
        original = io.StringIO()
        router = BridgeOutputRouter("stdout", original)
        payload = "界\n".encode()

        self.assertEqual(router.buffer.write(payload[:1]), 1)
        self.assertEqual(router.buffer.write(payload[1:]), len(payload) - 1)
        router.buffer.flush()

        self.assertEqual(original.getvalue(), "界\n")
        self.assertEqual(output, [("stdout", "界")])

    def test_binary_buffer_flushes_a_dangling_sequence_lossily(self) -> None:
        bridge = self.make_bridge()
        bridge.emit_output = lambda _stream, _text: None
        self.activate_bridge(bridge)
        original = io.StringIO()
        router = BridgeOutputRouter("stdout", original)

        router.buffer.write(b"\xe7\x95")
        router.buffer.flush()

        self.assertEqual(original.getvalue(), "�")

    def test_fileno_without_a_descriptor_raises_unsupported_operation(self) -> None:
        class TextOnlyStream:
            def __init__(self) -> None:
                self.text = ""

            def write(self, text: str) -> int:
                self.text += text
                return len(text)

            def flush(self) -> None:
                pass

            def writable(self) -> bool:
                return True

            def isatty(self) -> bool:
                return False

        router = BridgeOutputRouter("stdout", TextOnlyStream())

        with self.assertRaises(io.UnsupportedOperation):
            router.fileno()
        with self.assertRaises(io.UnsupportedOperation):
            router.buffer.fileno()

    def test_fileno_is_delegated_when_the_original_has_one(self) -> None:
        with open(os.devnull, "w") as original:
            router = BridgeOutputRouter("stdout", original)

            self.assertEqual(router.fileno(), original.fileno())
            self.assertEqual(router.buffer.fileno(), original.fileno())

    def test_subprocess_can_use_the_router_as_stdout(self) -> None:
        with tempfile.TemporaryFile("w+") as original:
            router = BridgeOutputRouter("stdout", original)

            subprocess.run(
                [sys.executable, "-c", "print('child output')"],
                stdout=router,
                check=True,
            )

            original.seek(0)
            self.assertEqual(original.read(), "child output\n")

    def test_uninstall_restores_the_previous_streams(self) -> None:
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        fake_stdout = io.StringIO()
        fake_stderr = io.StringIO()
        with BridgeOutputRouter._route_lock:
            saved_stdout_router = BridgeOutputRouter._stdout
            saved_stderr_router = BridgeOutputRouter._stderr
            BridgeOutputRouter._stdout = None
            BridgeOutputRouter._stderr = None
        try:
            sys.stdout = fake_stdout
            sys.stderr = fake_stderr
            BridgeOutputRouter.install()
            bridge = self.make_bridge()
            output = []
            bridge.emit_output = lambda stream, text: output.append((stream, text))
            self.activate_bridge(bridge)

            sys.stdout.buffer.write(b"installed out\n")
            sys.stderr.buffer.write(b"installed err\n")

            self.assertEqual(fake_stdout.getvalue(), "installed out\n")
            self.assertEqual(fake_stderr.getvalue(), "installed err\n")
            self.assertEqual(
                output,
                [("stdout", "installed out"), ("stderr", "installed err")],
            )

            BridgeOutputRouter.uninstall()

            self.assertIs(sys.stdout, fake_stdout)
            self.assertIs(sys.stderr, fake_stderr)
            sys.stdout.write("plain\n")
            self.assertEqual(fake_stdout.getvalue(), "installed out\nplain\n")
            self.assertEqual(
                output,
                [("stdout", "installed out"), ("stderr", "installed err")],
            )
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            with BridgeOutputRouter._route_lock:
                BridgeOutputRouter._stdout = saved_stdout_router
                BridgeOutputRouter._stderr = saved_stderr_router


if __name__ == "__main__":
    unittest.main()
