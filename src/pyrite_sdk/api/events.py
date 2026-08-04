from __future__ import annotations

import inspect
import traceback
from typing import Any, Awaitable, Callable, Mapping, Optional, TYPE_CHECKING
from uuid import uuid4

from ..models.schema import request

if TYPE_CHECKING:
    from ..core.bridge import Bridge

EventHandler = Callable[..., Optional[Awaitable[None]]]


class Subscription:
    """A live event subscription. Call :meth:`dispose` to stop delivery."""

    def __init__(self, bus: "PluginEventBus", subscription_id: str, topic: str):
        self._bus = bus
        self.id = subscription_id
        self.topic = topic
        self._disposed = False

    @property
    def disposed(self) -> bool:
        return self._disposed

    def dispose(self) -> None:
        if self._disposed:
            return
        self._disposed = True
        self._bus._remove(self.id)


class PluginEventBus:
    """Subscribe to host events and dispatch inbound ``ide.event.emit`` frames.

    Subscriptions are owned by the plugin session; the bus tracks them so
    :meth:`dispose_all` (called on plugin dispose) tears every one down. A
    handler that raises never propagates into the bridge event loop.
    """

    def __init__(self, bridge: "Bridge"):
        self._bridge = bridge
        self._subscriptions: dict[str, tuple[Subscription, EventHandler]] = {}

    def subscribe(
        self,
        topic: str,
        handler: EventHandler,
        *,
        filter: Optional[Mapping[str, Any]] = None,
        delivery: Optional[str] = None,
        debounce_ms: Optional[int] = None,
        callback: Optional[Callable] = None,
    ) -> Subscription:
        """Subscribe ``handler`` to ``topic``.

        ``delivery`` is one of ``every``/``latest``/``batch``/``debounce``/
        ``throttle``; ``debounce_ms`` sets the debounce/throttle/batch window.
        The returned :class:`Subscription` is registered immediately so events
        delivered before the host acknowledges the request are still routed.
        """
        subscription_id = uuid4().hex
        subscription = Subscription(self, subscription_id, topic)
        self._subscriptions[subscription_id] = (subscription, handler)

        payload: dict[str, Any] = {
            "subscriptionId": subscription_id,
            "topic": topic,
        }
        if filter:
            payload["filter"] = dict(filter)
        delivery_spec: dict[str, Any] = {}
        if delivery:
            delivery_spec["mode"] = delivery
        if debounce_ms is not None:
            delivery_spec["debounceMs"] = debounce_ms
        if delivery_spec:
            payload["delivery"] = delivery_spec

        def _on_response(error=None, **_):
            if error is not None:
                # The host rejected the subscription (unknown topic, denied
                # permission): drop it locally so it can be retried.
                self._remove(subscription_id)
            if callback is not None:
                callback(error=error)

        self._bridge.push_wait_response(
            request("sdk.events.subscribe", payload=payload),
            callback=_on_response,
        )
        return subscription

    def unsubscribe(self, subscription_id: str) -> None:
        self._remove(subscription_id)

    def dispose_all(self) -> None:
        """Release every subscription without notifying the host.

        Used on plugin dispose, when the whole session is going away.
        """
        for subscription, _ in list(self._subscriptions.values()):
            subscription._disposed = True
        self._subscriptions.clear()

    async def dispatch(self, subscription_id: str, topic: str, events: list) -> None:
        """Deliver inbound events to the subscription handler.

        Exceptions raised by the handler are caught and logged so one bad
        handler cannot stop the bridge event loop or other subscriptions.
        """
        entry = self._subscriptions.get(subscription_id)
        if entry is None:
            return
        subscription, handler = entry
        if subscription.disposed:
            return
        for event in events:
            try:
                result = handler(event) if not _wants_no_args(handler) else handler()
                if inspect.isawaitable(result):
                    await result
            except Exception:
                details = traceback.format_exc()
                message = f"Event handler for '{topic}' raised"
                self._log(f"{message}:\n{details}")
                report = getattr(self._bridge, "report_error", None)
                if callable(report):
                    report(
                        message,
                        traceback_text=details,
                        source=f"event:{topic}",
                    )

    def _remove(self, subscription_id: str) -> None:
        entry = self._subscriptions.pop(subscription_id, None)
        if entry is None:
            return
        subscription, _ = entry
        subscription._disposed = True
        # Best-effort notify the host; ignore failures during teardown.
        try:
            self._bridge.push_wait_response(
                request(
                    "sdk.events.unsubscribe",
                    payload={"subscriptionId": subscription_id},
                )
            )
        except Exception:
            pass

    def _log(self, message: str) -> None:
        log = getattr(self._bridge, "_log_internal", None)
        if callable(log):
            log(message)


def _wants_no_args(handler: EventHandler) -> bool:
    try:
        signature = inspect.signature(handler)
    except (TypeError, ValueError):
        return False
    return len(
        [
            p
            for p in signature.parameters.values()
            if p.kind
            in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        ]
    ) == 0
