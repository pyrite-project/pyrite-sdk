from __future__ import annotations

from typing import Any, Callable, Optional, TYPE_CHECKING

from ...models.schema import request

if TYPE_CHECKING:
    from ...core.bridge import Bridge


class Stubs:
    def __init__(self, bridge: Bridge):
        self._bridge = bridge

    def contribute(
        self,
        provider_id: str,
        profiles: list[dict[str, Any]],
        kind: str = "micropython",
        version: str = "",
        aliases: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        callback: Optional[Callable] = None,
    ):
        self._bridge.push_wait_response(
            request(
                "sdk.stubs.contribute",
                payload={
                    "provider_id": provider_id,
                    "kind": kind,
                    "version": version,
                    "profiles": profiles,
                    "aliases": aliases or [],
                    "metadata": metadata or {},
                },
            ),
            callback=callback,
        )

    def register_runtime(
        self,
        provider_id: str,
        profiles: list[dict[str, Any]],
        kind: str = "micropython",
        version: str = "",
        aliases: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        callback: Optional[Callable] = None,
    ):
        self._bridge.push_wait_response(
            request(
                "sdk.stubs.register_runtime",
                payload={
                    "provider_id": provider_id,
                    "kind": kind,
                    "version": version,
                    "profiles": profiles,
                    "aliases": aliases or [],
                    "metadata": metadata or {},
                },
            ),
            callback=callback,
        )

    def revoke(self, provider_id: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request("sdk.stubs.revoke", payload={"provider_id": provider_id}),
            callback=callback,
        )

    def list(self, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(request("sdk.stubs.list"), callback=callback)

    def get(self, provider_id: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request("sdk.stubs.get", payload={"provider_id": provider_id}),
            callback=callback,
        )

    def resolve_layers(
        self,
        layers: list[dict[str, str]],
        callback: Optional[Callable] = None,
    ):
        self._bridge.push_wait_response(
            request("sdk.stubs.resolve_layers", payload={"layers": layers}),
            callback=callback,
        )
