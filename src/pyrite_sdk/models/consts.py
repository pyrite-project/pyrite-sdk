from enum import StrEnum, Enum

class MessageCommandsIDERequest(str, Enum):
    EVENT_CALLBACK = "Commands.IDE.Request.EventCallback"
    LIFECYCLE_HOOKS = "Commands.IDE.Request.LifecycleHooks"
    GET_PAGES = "Commands.IDE.Request.GetPages"
    REQUEST = "Commands.IDE.Request.Request"

class MessageCommandsIDEResponse(str, Enum):
    GET_PATH = "Commands.IDE.Response.GetPath"
    ERROR_RESPONSE = "Commands.IDE.Response.ErrorResponse"
    RESPONSE = "Commands.IDE.Response.Response"

class MessageCommandsSDKRequest(str, Enum):
    GET_PATH = "Commands.SDK.Request.GetPath"
    REFRESH = "Commands.SDK.Request.Refresh"
    SET_VAR = "Commands.SDK.Request.SetVar"
    REQUEST = "Commands.SDK.Request.Request"

class MessageCommandsSDKResponse(str, Enum):
    ERROR_RESPONSE = "Commands.SDK.Response.ErrorResponse"
    RESPONSE = "Commands.SDK.Response.Response"

class MessageCommandsIDE:
    REQUEST = MessageCommandsIDERequest
    RESPONSE = MessageCommandsIDEResponse

class MessageCommandsSDK:
    REQUEST = MessageCommandsSDKRequest
    RESPONSE = MessageCommandsSDKResponse

class MessageCommands:
    IDE = MessageCommandsIDE
    SDK = MessageCommandsSDK

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
