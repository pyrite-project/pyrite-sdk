from enum import Enum

class MessageCommands(str, Enum):
    GET_RFW_CODE = "Commands.GetRfwCode"
    EVENT_CALLBACK = "Commands.EventCallback"
    RESPONSE = "Commands.Response"
    ERROR_RESPONSE = "Commands.ErrorResponse"
    SEND = "Commands.Send"

class Error(str, Enum):
    KEY_NOT_FOUND = "Error.KetNotFound"