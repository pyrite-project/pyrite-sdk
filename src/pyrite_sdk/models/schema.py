from pydantic import BaseModel, Field
from .consts import *
from typing import Optional, Any, Union

class CallbackData(BaseModel):
    args: dict = Field(..., description="The arguments")
    event: str = Field(..., description="The event name")

class MessageData(BaseModel):
    err: Optional[str] = Field(None, description="The error")
    pages: Optional[dict] = Field(None, description="The map to pages RFW code and name")
    page: Optional[str] = Field(None, description="The page to access")
    callback: Optional[CallbackData] = Field(None, description="The callback data")
    lifecycle_hook: Optional[LifecycleHooks] = Field(None, alias="lifecycleHook", description="The LifecycleHook to run")
    path_type: Optional[PathType] = Field(None, alias="pathType")
    var_name: Optional[str] = Field(None, alias="varName", description="The variable name to set")
    var_value: Optional[Any] = Field(None, alias="varValue", description="The variable value to set")
    path: Optional[str] = Field(None, description="The path to get")
    others: Optional[str] = Field(None, description="The other data")

    class Config:
        allow_population_by_field_name = True

class Message(BaseModel):
    cmd: Union[MessageCommandsIDERequest, MessageCommandsIDEResponse, MessageCommandsSDKRequest, MessageCommandsSDKResponse] = Field(..., description="The command")
    data: MessageData = Field(..., description="The data")
    source: Optional[Any] = Field(None, description="The source message")
