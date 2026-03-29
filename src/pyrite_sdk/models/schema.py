from pydantic import BaseModel, Field
from .consts import *
from typing import Optional

class MessageData(BaseModel):
    err: Optional[str] = Field(None, description="The error")
    manager: Optional[str] = Field(None, description="The manager RFW code")

class Message(BaseModel):
    cmd: MessageCommands = Field(..., description="The command")
    data: MessageData = Field(..., description="The data")
    source: Optional["Message"] = Field(None, description="The source message")

Message.model_rebuild()

# x = Message.model_validate_json('{"cmd":"GetRfwCode","data":{"args":"manager0"}}')
# print(x)
