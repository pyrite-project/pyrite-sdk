from enum import StrEnum, Enum

class MessageCommands(str, Enum):
    GET_PAGES = "Commands.GetPages"
    GET_PATH = "Commands.GetPath"
    REFRESH = "Commands.Refresh"
    EVENT_CALLBACK = "Commands.EventCallback"
    LIFECYCLE_HOOKS = "Commands.LifecycleHooks"
    ERROR_RESPONSE = "Commands.ErrorResponse"
    RESPONSE = "Commands.Response"
    SEND = "Commands.Send"

class PathType(str, Enum):
    ASSETS = "PathType.Assets"

class LifecycleHooks(str, Enum):
    ON_INSTALL = "LifecycleHooks.OnInstall"
    ON_START = "LifecycleHooks.OnStart"
    ON_PAUSE = "LifecycleHooks.OnPause"
    ON_RESUME = "LifecycleHooks.OnResume"
    ON_DISPOSE = "LifecycleHooks.OnDispose"
    ON_UNINSTALL = "LifecycleHooks.OnUninstall"

class Error(str, Enum):
    KEY_NOT_FOUND = "Error.KeyNotFound"
    API_NOT_FOUND = "Error.ApiNotFound"

class Ui(StrEnum):
    LTR = "ltr"
    AppBar = "appBar"
    Title = "title"
    root = "root"

class PackageCore(StrEnum):
    widgets = "core.widgets"
    material = "core.material"

class Package:
    core = PackageCore
