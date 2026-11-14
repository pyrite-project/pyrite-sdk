import unittest
from typing import Any, Callable, Optional

from pyrite_sdk.api.serial import Serial
from pyrite_sdk.models.schema import Envelope


class RecordingBridge:
    def __init__(self) -> None:
        self.envelopes: list[Envelope] = []

    def push_wait_response(
        self,
        envelope: Envelope,
        callback: Optional[Callable[..., Any]] = None,
        client: Any = None,
    ) -> bool:
        self.envelopes.append(envelope)
        return True


class SerialSendTest(unittest.TestCase):
    def _send(self, data: Any) -> Any:
        bridge = RecordingBridge()
        Serial(bridge).send(data)
        self.assertEqual(len(bridge.envelopes), 1)
        envelope = bridge.envelopes[0]
        self.assertEqual(envelope.type, "sdk.serial.send")
        # The bridge transport serializes any queued envelope to JSON.
        envelope.model_dump_json(by_alias=True)
        return envelope.payload["data"]

    def test_bytearray_is_sent_as_byte_values(self):
        self.assertEqual(self._send(bytearray([0xFF])), [255])

    def test_memoryview_is_sent_as_byte_values(self):
        self.assertEqual(self._send(memoryview(b"\xff")), [255])

    def test_memoryview_slice_is_sent_as_byte_values(self):
        self.assertEqual(self._send(memoryview(b"\x00\xff")[1:]), [255])

    def test_bytes_are_sent_as_byte_values(self):
        self.assertEqual(self._send(b"\xff\x00"), [255, 0])

    def test_integer_sequences_are_forwarded(self):
        self.assertEqual(self._send([255, 0]), [255, 0])
        self.assertEqual(self._send((255,)), [255])

    def test_text_is_forwarded_unchanged(self):
        self.assertEqual(self._send("hello"), "hello")

    def test_unsupported_value_raises_and_registers_no_request(self):
        bridge = RecordingBridge()
        with self.assertRaisesRegex(TypeError, "serial.send"):
            Serial(bridge).send(object())
        self.assertEqual(bridge.envelopes, [])

    def test_sequence_with_non_integer_values_is_rejected(self):
        bridge = RecordingBridge()
        with self.assertRaisesRegex(TypeError, "serial.send"):
            Serial(bridge).send([0, "x"])
        self.assertEqual(bridge.envelopes, [])


if __name__ == "__main__":
    unittest.main()
