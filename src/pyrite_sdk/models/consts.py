from enum import StrEnum

class MessageCommands(StrEnum):
    GET_PAGES = "Commands.GetPages"
    EVENT_CALLBACK = "Commands.EventCallback"
    RESPONSE = "Commands.Response"
    ERROR_RESPONSE = "Commands.ErrorResponse"
    SEND = "Commands.Send"
    LIFECYCLE_HOOKS = "Commands.LifecycleHooks"

class LifecycleHooks(StrEnum):
    ON_INSTALL = "LifecycleHooks.OnInstall"
    ON_START = "LifecycleHooks.OnStart"
    ON_PAUSE = "LifecycleHooks.OnPause"
    ON_RESUME = "LifecycleHooks.OnResume"
    ON_DISPOSE = "LifecycleHooks.OnDispose"
    ON_UNINSTALL = "LifecycleHooks.OnUninstall"

class Error(StrEnum):
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
