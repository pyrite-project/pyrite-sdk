from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from uuid import uuid4
import time
from .consts import PathScope, LifecycleHook, ErrorCode


def new_id() -> str:
    return uuid4().hex

def now() -> int:
    return int(time.time() * 1000)


class PagePayload(BaseModel):
    pages: Dict[str, str]


class VarSetPayload(BaseModel):
    name: str
    value: Any


class PathRequestPayload(BaseModel):
    scope: PathScope


class LocalWorkspaceRequestPathPayload(BaseModel):
    path: str


class LocalWorkspaceRequestCreatePayload(BaseModel):
    path: str


class LocalWorkspaceRequestRenamePayload(BaseModel):
    path: str
    new_name: str


class LocalWorkspaceRequestCopyPayload(BaseModel):
    src: str
    dst: str


class LocalWorkspaceRequestWritePayload(BaseModel):
    path: str
    content: str


class LocalWorkspaceRequestUploadPayload(BaseModel):
    local_path: str
    board_path: str


class LocalWorkspaceRequestDownloadPayload(BaseModel):
    board_path: str
    local_path: str


class LocalWorkspaceRequestUniqueNamePayload(BaseModel):
    name: str
    is_folder: bool = False


class EventCallbackPayload(BaseModel):
    page: str
    name: str
    args: Dict[str, Any]


class LifecyclePayload(BaseModel):
    hook: LifecycleHook


class RefreshPayload(BaseModel):
    pass


class OkResponsePayload(BaseModel):
    data: Optional[Any] = None


class ErrorResponsePayload(BaseModel):
    code: ErrorCode
    message: str
    details: Optional[Any] = None


class PathResponsePayload(BaseModel):
    scope: PathScope
    path: str

class LocalWorkspaceResponseListDir(BaseModel):
    dir_list: list[str]

class Envelope(BaseModel):
    version: str = "0.0"
    id: str = Field(default_factory=new_id)
    type: str
    payload: dict
    data: Optional[Any] = None
    reply_to: Optional[str] = None
    timestamp: int = Field(default_factory=now)


def request(type_: str, payload: Optional[BaseModel] = None, data: Optional[Any] = None) -> Envelope:
    return Envelope(type=type_, payload=payload.dict() if payload else {}, data=data)


def ok(original: Envelope, data: Any = None) -> Envelope:
    role = original.type.split(".", 1)[0]
    return Envelope(
        type=f"{role}.response.ok",
        payload=OkResponsePayload(data=data).dict(),
        reply_to=original.id,
    )


def err(original: Envelope, code: ErrorCode, message: str,
        details: Any = None) -> Envelope:
    role = original.type.split(".", 1)[0]
    return Envelope(
        type=f"{role}.response.error",
        payload=ErrorResponsePayload(
            code=code, message=message, details=details
        ).dict(),
        reply_to=original.id,
    )
