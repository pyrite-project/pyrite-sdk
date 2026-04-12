from pydantic import BaseModel, Field
from .consts import *
from typing import Optional, Any

class CallbackData(BaseModel):
    args: dict = Field(..., description="The arguments")
    event: str = Field(..., description="The event name")

class MessageData(BaseModel):
    err: Optional[str] = Field(None, description="The error")
    pages: Optional[dict] = Field(None, description="The map to pages RFW code and name")
    page: Optional[str] = Field(None, description="The page to access")
    callback: Optional[CallbackData] = Field(None, description="The callback data")
    lifecycle_hook: Optional[LifecycleHooks] = Field(None, alias="lifecycleHook", description="The LifecycleHook to run")
    others: Optional[str] = Field(None, description="The other data")

class Message(BaseModel):
    cmd: MessageCommands = Field(..., description="The command")
    data: MessageData = Field(..., description="The data")
    source: Optional[Any] = Field(None, description="The source message")
