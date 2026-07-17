from enum import StrEnum, Enum


class PathScope(str, Enum):
    PLUGIN = "plugin"
    CACHE = "cache"
    DATA = "data"
    TEMP = "temp"


class LifecycleHook(str, Enum):
    INSTALL = "install"
    START = "start"
    PAUSE = "pause"
    RESUME = "resume"
    DISPOSE = "dispose"
    UNINSTALL = "uninstall"


class ErrorCode(str, Enum):
    KEY_NOT_FOUND = "key_not_found"
    API_NOT_FOUND = "api_not_found"
    INVALID_REQUEST = "invalid_request"
    INTERNAL_ERROR = "internal_error"
    TIMEOUT = "timeout"


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
