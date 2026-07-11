from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List
from uuid import uuid4
import time
from .consts import PathScope, LifecycleHook, ErrorCode


def new_id() -> str:
    return uuid4().hex

def now() -> int:
    return int(time.time() * 1000)


class PagePayload(BaseModel):
    pages: Dict[str, str]


class CallbackPayload(BaseModel):
    callbacks: List[str]


class VarSetPayload(BaseModel):
    name: str
    value: Any


class CallbackBindingPayload(BaseModel):
    name: str
    var: str


class PathRequestPayload(BaseModel):
    scope: PathScope


class FileRequestPathPayload(BaseModel):
    path: str


class FileRequestCreatePayload(BaseModel):
    path: str


class FileRequestRenamePayload(BaseModel):
    path: str
    new_name: str


class FileRequestCopyPayload(BaseModel):
    src: str
    dst: str


class FileRequestWritePayload(BaseModel):
    path: str
    content: str


class FileRequestUploadPayload(BaseModel):
    local_path: str
    board_path: str


class FileRequestDownloadPayload(BaseModel):
    board_path: str
    local_path: str


class FileRequestUniqueNamePayload(BaseModel):
    name: str
    is_folder: bool = False


class DialogOpenFolderPayload(BaseModel):
    title: Optional[str] = None
    initial_directory: Optional[str] = None


class EditorSetTextPayload(BaseModel):
    text: str


class EditorInsertTextPayload(BaseModel):
    text: str


class EditorReplaceRangePayload(BaseModel):
    start: int
    end: int
    text: str


class EditorGetLineTextPayload(BaseModel):
    line: int


class EditorCursorPositionPayload(BaseModel):
    line: int
    column: int


class EditorSelectionPayload(BaseModel):
    start: int
    end: int


class EditorFindPayload(BaseModel):
    word: str
    match_case: bool = False
    whole_word: bool = False


class EditorFindRegexPayload(BaseModel):
    pattern: str


class EditorOpenFilePayload(BaseModel):
    path: str


class EditorCloseTabPayload(BaseModel):
    path: str


class EditorGhostTextPayload(BaseModel):
    text: str
    line: int
    column: int


class EditorScrollToLinePayload(BaseModel):
    line: int


class EventCallbackPayload(BaseModel):
    page: str
    name: str
    args: Dict[str, Any]


class RouterPushPayload(BaseModel):
    page: str


class RouterPopPayload(BaseModel):
    pass


class RouterReplacePayload(BaseModel):
    page: str


class RouterGotoPayload(BaseModel):
    page: str


class RouterSyncPayload(BaseModel):
    page: str
    stack: List[str]


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


class PersistenceGetPayload(BaseModel):
    group: str
    key: str


class PersistenceSetPayload(BaseModel):
    group: str
    key: str
    value: Any


class PersistenceDeletePayload(BaseModel):
    group: str
    key: str


class PersistenceListKeysPayload(BaseModel):
    group: str


class PersistenceClearPayload(BaseModel):
    group: str

class FileResponseListDir(BaseModel):
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
    if payload is None:
        p = {}
    elif isinstance(payload, dict):
        p = payload
    else:
        p = payload.dict()
    return Envelope(type=type_, payload=p, data=data)


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
