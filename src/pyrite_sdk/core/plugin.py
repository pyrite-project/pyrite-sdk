from abc import ABC, abstractmethod
import inspect
from typing import Any
from ..core.bridge import Bridge
from .context import PluginContext
from ..api.file import *
from ..api.editor import Editor
from ..api.persistence import Persistence
from ..api.data import Theme, I18n, Stubs
from ..api.settings import Settings
from ..api.serial import Serial
from ..api.path import Path as SdkPath
from ..api.message import Message
from ..api.clipboard import Clipboard
from ..api.dialog import Dialog
from ..api.events import PluginEventBus
from ..api.document import EditorDocuments
from ..api.environment import Environment
from ..api.runtime import Runtime
from ..api.tab import Tabs
from ..api.view import Views
from ..api.resources import Resources
from ..api.commands import Commands
from ..api.configuration import Configuration


class BasePlugin(ABC):
    def __init__(self, queue_size: int = 50) -> None:
        self.bridge = Bridge(self, queue_size)
        self.start = self.bridge.start
        self.run = self.bridge.start
        self.path = SdkPath(self.bridge)
        self.settings = Settings(self.bridge)
        self.message = Message(self.bridge)
        self.clipboard = Clipboard(self.bridge)
        self.dialog = Dialog(self.bridge)
        self.resources = Resources()
        self.events = PluginEventBus(self.bridge)
        self.commands = Commands(self.bridge)
        self.configuration = Configuration(self.bridge, self.events)

    @property
    def context(self) -> PluginContext:
        return self.bridge.context

    def on_pause(self) -> Any: ...
    def on_resume(self) -> Any: ...
    def on_dispose(self) -> Any: ...


class UiPlugin(BasePlugin):
    def __init__(self, queue_size: int = 50) -> None:
        super().__init__(queue_size)
        self.file = File(self.bridge)
        self.board = Board(self.bridge)
        self.editor = Editor(self.bridge)
        self.persistence = Persistence(self.bridge)
        self.theme = Theme(self.bridge)
        self.i18n = I18n(self.bridge)
        self.stubs = Stubs(self.bridge)
        self.serial = Serial(self.bridge)
        self.documents = EditorDocuments(self.bridge, self.events)
        self.runtime = Runtime(self.bridge, self.events)
        self.tabs = Tabs(self.bridge)
        self.views = Views(self.bridge)
        self.env = Environment(self.bridge)

    @abstractmethod
    def on_start(self) -> Any: ...


class ServicePlugin(BasePlugin):
    def __init__(self, queue_size: int = 50) -> None:
        super().__init__(queue_size)
        self.file = File(self.bridge)
        self.board = Board(self.bridge)
        self.persistence = Persistence(self.bridge)
        self.theme = Theme(self.bridge)
        self.i18n = I18n(self.bridge)
        self.stubs = Stubs(self.bridge)
        self.documents = EditorDocuments(self.bridge, self.events)
        self.runtime = Runtime(self.bridge, self.events)
        self.serial = Serial(self.bridge)
        self.env = Environment(self.bridge)

    @abstractmethod
    def on_start(self) -> Any: ...


class DataPlugin(BasePlugin):
    def __init__(self, queue_size: int = 50) -> None:
        super().__init__(queue_size)
        self.theme = Theme(self.bridge)
        self.i18n = I18n(self.bridge)
        self.stubs = Stubs(self.bridge)

    async def on_start(self) -> None:
        result = self.on_contribute()
        if inspect.isawaitable(result):
            await result
        self.bridge.stop_when_idle()

    @abstractmethod
    def on_contribute(self) -> Any: ...

    def run_once(self) -> None:
        self.start()
