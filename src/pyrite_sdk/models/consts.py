from enum import Enum

class MessageCommands(str, Enum):
    GET_PAGES = "Commands.GetPages"
    EVENT_CALLBACK = "Commands.EventCallback"
    RESPONSE = "Commands.Response"
    ERROR_RESPONSE = "Commands.ErrorResponse"
    SEND = "Commands.Send"
    LIFECYCLE_HOOKS = "Commands.LifecycleHooks"

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
