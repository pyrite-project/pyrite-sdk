from enum import Enum


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
    PROTOCOL_ERROR = "protocol_error"
    PERMISSION_DENIED = "permission_denied"
    UNKNOWN_COMMAND = "unknown_command"
    INVALID_CONTEXT = "invalid_context"
    KEY_NOT_FOUND = "key_not_found"
    API_NOT_FOUND = "api_not_found"
    INVALID_REQUEST = "invalid_request"
    INTERNAL_ERROR = "internal_error"
    TIMEOUT = "timeout"
