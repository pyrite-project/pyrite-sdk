from pydantic import BaseModel, Field
from .consts import *
from typing import Optional

class CallbackData(BaseModel):
    args: dict = Field(..., description="The arguments")
    event: str = Field(..., description="The event name")

class MessageData(BaseModel):
    err: Optional[str] = Field(None, description="The error")
    managers: Optional[dict] = Field(None, description="The map to manager RFW code and reg name")
    manager: Optional[str] = Field(None, description="The manager to access")
    callback: Optional[CallbackData] = Field(None, description="The callback data")
    others: Optional[str] = Field(None, description="The other data")

class Message(BaseModel):
    cmd: MessageCommands = Field(..., description="The command")
    data: MessageData = Field(..., description="The data")
    source: Optional["Message"] = Field(None, description="The source message")

Message.model_rebuild()

# x = Message.model_validate_json('{"cmd":"GetRfwCode","data":{"args":"manager0"}}')
# print(x)
