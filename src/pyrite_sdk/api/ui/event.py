from pyrite_sdk.utils.ui import RFWSerializable, DataSerializer
from typing import Any, Callable, Optional

class Event(RFWSerializable):
    def __init__(self, callback: Callable[..., Any], args: dict[str, Any], event: str = "") -> None:
        self.callback: Callable[..., Any] = callback
        self.event: str = event
        self.args: dict[str, Any] = args
        self.events: Optional[Events] = None

    def get_event_name(self) -> Optional[str]:
        if self.events is None:
            return None
        if self.event:
            if self.event in self.events:
                raise Exception(f"Event {self.event} already exists")
            return self.event
        print("EVENTS", self.events)
        return f"event_{len(self.events)}"

    def setup(self) -> None:
        if self.events is None:
            return
        self.event = self.get_event_name()
        if self.event is not None:
            self.events[self.event] = self.callback

    def get_args(self) -> str:
        return DataSerializer(self.args).to_rfw()

    def to_rfw(self) -> str:
        return f'event "{self.event}" {self.get_args()}'

class Events(dict[str, Callable[..., Any]]):
    def __init__(self) -> None:
        super().__init__()
