from enum import Enum

class MessageCommands(str, Enum):
    GET_RFW_CODE = "GetRfwCode"
    RESPONSE = "Response"
    ERROR_RESPONSE = "ErrorResponse"

class Error(str, Enum):
    KEY_NOT_FOUND = "ERR_KEY_NOT_FOUND"