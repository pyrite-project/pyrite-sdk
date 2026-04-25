from pydantic import BaseModel, Field
from .consts import *
from typing import Optional, Any

class CallbackData(BaseModel):
    args: dict = Field(..., description="The arguments")
    event: str = Field(..., description="The event name")

class MessageData(BaseModel):
    err: Optional[str] = None
    pages: Optional[dict] = None
    page: Optional[str] = None
    callback: Optional[CallbackData] = None
    lifecycle_hook: Optional[LifecycleHooks] = None
    others: Optional[str] = None

class Message(BaseModel):
    cmd: MessageCommands = Field(..., description="The command")
    data: MessageData = Field(..., description="The data")
    source: Optional[Any] = None
