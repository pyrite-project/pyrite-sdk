from pyrite_sdk.utils.ui import RFWSerializable, DataSerializer

class Event(RFWSerializable):
    def __init__(self, callback: callable, args: dict, event: str = ""):
        self.callback = callback
        self.event = event
        self.args = args
        self.events: Events | None = None

    def get_event_name(self):
        if self.events is None:
            return
        if self.event:
            if self.event in self.events:
                raise Exception(f"Event {self.event} already exists")
            return self.event
        print("EVENTS", self.events)
        return f"event_{len(self.events)}"

    def setup(self):
        if self.events is None:
            return
        self.event = self.get_event_name()
        self.events[self.event] = self.callback

    def get_args(self):
        return DataSerializer(self.args).to_rfw()

    def to_rfw(self):
        return f"event \"{self.event}\" {self.get_args()}"

class Events(dict[str:callable]):
    def __init__(self):
        super().__init__()
