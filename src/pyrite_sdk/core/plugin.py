from abc import ABC, abstractmethod
from ..interfaces.ui import PageType
from ..core.bridge import Bridge
from ..api.file import *
from ..api.editor import Editor
from ..api.ui.router import Router
from ..api.persistence import Persistence
from ..api.data import Theme, I18n, Stubs
from ..api.settings import Settings
from ..api.serial import Serial
from ..api.path import Path as SdkPath
from ..api.message import Message
from ..api.dialog import Dialog

class BasePlugin(ABC):
    def __init__(self, queue_size: int = 50) -> None:
        self.bridge = Bridge(self, queue_size)
        self.start = self.bridge.start
        self.run = self.bridge.start
        self.path = SdkPath(self.bridge)
        self.settings = Settings(self.bridge)
        self.message = Message(self.bridge)
        self.dialog = Dialog(self.bridge)

    def on_pause(self): ...
    def on_resume(self): ...
    def on_refresh(self): ...
    def on_dispose(self): ...


class UiPlugin(BasePlugin):
    def __init__(self, queue_size: int = 50) -> None:
        super().__init__(queue_size)
        self.pages: dict[str, PageType] = {}
        self.file = File(self.bridge)
        self.board = Board(self.bridge)
        self.editor = Editor(self.bridge)
        self.router = Router(self.bridge)
        self.persistence = Persistence(self.bridge)
        self.theme = Theme(self.bridge)
        self.i18n = I18n(self.bridge)
        self.stubs = Stubs(self.bridge)
        self.serial = Serial(self.bridge)

    @abstractmethod
    def on_start(self): ...


class ServicePlugin(BasePlugin):
    def __init__(self, queue_size: int = 50) -> None:
        super().__init__(queue_size)
        self.file = File(self.bridge)
        self.board = Board(self.bridge)
        self.persistence = Persistence(self.bridge)
        self.theme = Theme(self.bridge)
        self.i18n = I18n(self.bridge)
        self.stubs = Stubs(self.bridge)
        self.serial = Serial(self.bridge)

    @abstractmethod
    def on_start(self): ...


class DataPlugin(BasePlugin):
    def __init__(self, queue_size: int = 50) -> None:
        super().__init__(queue_size)
        self.theme = Theme(self.bridge)
        self.i18n = I18n(self.bridge)
        self.stubs = Stubs(self.bridge)

    def on_start(self):
        self.on_contribute()
        self.bridge.stop_when_idle()

    @abstractmethod
    def on_contribute(self): ...

    def run_once(self):
        self.start()
