from pyrite_sdk.utils.ui import RFWSerializable, DataSerializer
from typing import Any, Callable, Optional

class Event(RFWSerializable):
    def __init__(self, callback: Callable[..., Any], args: Optional[dict[str, Any]] = None, event: str = "") -> None:
        self.callback: Callable[..., Any] = callback
        self.event: str = event
        self._explicit_event: bool = bool(event)
        self._default_event: Optional[str] = None
        self.args: dict[str, Any] = args or {}
        self.events: Optional[dict[str, Callable[..., Any]]] = None
        self._setup_done: bool = False
        self._setup_events: Optional[dict[str, Callable[..., Any]]] = None

    def set_default_event(self, widget_id: int, event: str) -> None:
        self._default_event = f"callback-{widget_id}-{event}"

    def get_event_name(self) -> Optional[str]:
        if self.events is None:
            return None
        if self._explicit_event:
            if self.event in self.events:
                raise Exception(f"Event {self.event} already exists")
            return self.event
        if self._default_event is None:
            raise Exception("Event default name requires a widget event")
        if self._default_event in self.events:
            raise Exception(f"Event {self._default_event} already exists")
        return self._default_event

    def setup(self) -> None:
        if self.events is None:
            return
        if self._setup_done and self._setup_events is self.events:
            return
        self.event = self.get_event_name()
        if self.event is not None:
            self.events[self.event] = self.callback
            self._setup_done = True
            self._setup_events = self.events

    def get_args(self) -> str:
        return DataSerializer(self.args).to_rfw()

    def to_rfw(self) -> str:
        return f'event "{self.event}" {self.get_args()}'
