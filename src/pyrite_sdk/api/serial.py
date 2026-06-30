from __future__ import annotations

from typing import Callable, Optional, Sequence, TYPE_CHECKING

from ..models.schema import request

if TYPE_CHECKING:
    from ..core.bridge import Bridge


class Serial:
    def __init__(self, bridge: Bridge):
        self._bridge = bridge

    def list_ports(self, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request("sdk.serial.list_ports"),
            callback=callback,
        )

    def get_status(self, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request("sdk.serial.get_status"),
            callback=callback,
        )

    def connect(self, port: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request("sdk.serial.connect", payload={"port": port}),
            callback=callback,
        )

    def disconnect(self, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request("sdk.serial.disconnect"),
            callback=callback,
        )

    def send(self, data: str | bytes | Sequence[int], callback: Optional[Callable] = None):
        if isinstance(data, bytes):
            payload_data = list(data)
        else:
            payload_data = data
        self._bridge.push_wait_response(
            request("sdk.serial.send", payload={"data": payload_data}),
            callback=callback,
        )

    def send_command(
        self,
        command: str,
        chunked: bool = True,
        callback: Optional[Callable] = None,
    ):
        self._bridge.push_wait_response(
            request(
                "sdk.serial.send_command",
                payload={"command": command, "chunked": chunked},
            ),
            callback=callback,
        )

    def read(
        self,
        timeout_ms: int = 1000,
        max_bytes: Optional[int] = None,
        callback: Optional[Callable] = None,
    ):
        payload = {"timeout_ms": timeout_ms}
        if max_bytes is not None:
            payload["max_bytes"] = max_bytes
        self._bridge.push_wait_response(
            request("sdk.serial.read", payload=payload),
            callback=callback,
        )

    def run_python(
        self,
        code: str,
        timeout_ms: int = 20000,
        callback: Optional[Callable] = None,
    ):
        self._bridge.push_wait_response(
            request(
                "sdk.serial.run_python",
                payload={"code": code, "timeout_ms": timeout_ms},
            ),
            callback=callback,
        )

    def set_baud_rate(self, value: int, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request("sdk.serial.set_baud_rate", payload={"value": value}),
            callback=callback,
        )

    def set_auto_reconnect(self, value: bool, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request("sdk.serial.set_auto_reconnect", payload={"value": value}),
            callback=callback,
        )
