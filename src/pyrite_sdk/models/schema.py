from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Any, Dict, List
from uuid import uuid4
import time
from .consts import PathScope, LifecycleHook, ErrorCode


def new_id() -> str:
    return uuid4().hex


def now() -> int:
    return int(time.time() * 1000)


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
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    protocol_version: int = Field(
        default=1,
        ge=1,
        validation_alias="protocolVersion",
        serialization_alias="protocolVersion",
    )
    plugin_id: str = Field(
        default="standalone",
        min_length=1,
        validation_alias="pluginId",
        serialization_alias="pluginId",
    )
    session_id: str = Field(
        default="standalone",
        min_length=1,
        validation_alias="sessionId",
        serialization_alias="sessionId",
    )
    generation: int = Field(default=1, ge=1)
    request_id: str = Field(
        default_factory=new_id,
        min_length=1,
        validation_alias="requestId",
        serialization_alias="requestId",
    )
    reply_to: Optional[str] = Field(
        default=None,
        validation_alias="replyTo",
        serialization_alias="replyTo",
    )
    sequence: int = Field(default=1, ge=1)
    type: str = Field(min_length=1)
    payload: dict
    data: Optional[Any] = None
    timestamp: int = Field(default_factory=now)
    deadline: Optional[int] = Field(
        default=None,
        ge=0,
        exclude_if=lambda value: value is None,
    )

    def json(self, *args, **kwargs) -> str:
        kwargs.setdefault("by_alias", True)
        return self.model_dump_json(*args, **kwargs)


def request(
    type_: str,
    payload: Optional[BaseModel] = None,
    data: Optional[Any] = None,
    *,
    deadline: Optional[int] = None,
) -> Envelope:
    if payload is None:
        p = {}
    elif isinstance(payload, dict):
        p = payload
    else:
        p = payload.model_dump()
    return Envelope(type=type_, payload=p, data=data, deadline=deadline)


def ok(original: Envelope, data: Any = None) -> Envelope:
    role = original.type.split(".", 1)[0]
    return Envelope(
        type=f"{role}.response.ok",
        payload=OkResponsePayload(data=data).model_dump(),
        plugin_id=original.plugin_id,
        session_id=original.session_id,
        generation=original.generation,
        reply_to=original.request_id,
    )


def err(
    original: Envelope, code: ErrorCode, message: str, details: Any = None
) -> Envelope:
    role = original.type.split(".", 1)[0]
    return Envelope(
        type=f"{role}.response.error",
        payload=ErrorResponsePayload(
            code=code, message=message, details=details
        ).model_dump(),
        plugin_id=original.plugin_id,
        session_id=original.session_id,
        generation=original.generation,
        reply_to=original.request_id,
    )
