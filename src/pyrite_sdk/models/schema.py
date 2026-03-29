from pydantic import BaseModel, Field
from .consts import *
from typing import Optional

class MessageDataArgs(BaseModel):
    manager: str = Field(..., description="The manager name")

class MessageData(BaseModel):
    args: Optional[MessageDataArgs] = Field(None, description="The arguments")
    err: Optional[str] = Field(None, description="The error")

class BasicMessage(BaseModel):
    cmd: MessageCommands = Field(..., description="The command")
    data: MessageData = Field(..., description="The data")
    source: Optional["BasicMessage"] = Field(None, description="The source message")

BasicMessage.model_rebuild()
