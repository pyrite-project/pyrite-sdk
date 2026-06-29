# PyriteSDK WebSocket 传输数据规范

## 1. 设计原则

1. **类型安全** —— 每个消息类型有独立的 Payload 模型
2. **请求-响应关联** —— 每个请求携带 `id`，响应通过 `reply_to` 关联
3. **双向对称** —— IDE 和 SDK 使用相同的消息框架
4. **版本化** —— 协议版本号协商
5. **可扩展** —— 通过 `type` 分发，新增类型不影响现有处理

---

## 2. 传输层

| 项目 | 值 |
| --- | --- |
| 协议 | WebSocket (RFC 6455) |
| 地址 | `ws://localhost:{port}` |
| 端口 | 环境变量`PYRITE_IDE_PLUGIN_PORT` |
| 编码 | UTF-8 |
| 帧格式 | 文本帧 (Text Frame) |
| 序列化 | JSON |

---

## 3. 消息信封（Message Envelope）

所有消息共用一个外层信封：

```python
class Envelope(BaseModel):
    version: str = "0.0"           # 协议版本
    id: str                        # 消息唯一 ID (UUID v4)
    type: str                      # 消息类型，见第4节
    payload: dict                  # 具体载荷
    data: Optional[Any] = None     # 附加数据（部分消息类型使用）
    reply_to: Optional[str] = None # 回复目标的 id（仅响应消息）
    timestamp: int                 # Unix 毫秒时间戳
```

### JSON 示例

```json
{
  "version": "0.0",
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "type": "sdk.page.push",
  "payload": { ... },
  "timestamp": 1719360000000
}
```

---

## 4. 消息类型（type 字段）

### 4.1 `SDK -> IDE`

|type|说明|
|---|---|
|`sdk.page.push`|推送页面 UI 描述|
|`sdk.var.set`|设置响应式变量|
|`sdk.path.request`|请求资源路径|
|`sdk.request`|通用请求|
|`sdk.file.get_root_dir`|请求本地工作区根目录|
|`sdk.file.get_dir_list`|请求目录下的文件列表（path 通过 `data` 字段传递）|
|`sdk.file.create_file`|创建文件|
|`sdk.file.create_folder`|创建文件夹|
|`sdk.file.get_focus_file_node`|获取当前聚焦的文件节点|
|`sdk.file.get_focus_folder_node`|获取当前聚焦的文件夹节点|
|`sdk.file.open_file`|打开文件|
|`sdk.file.open_folder`|打开文件夹|
|`sdk.file.rename_file`|重命名文件|
|`sdk.file.delete_file`|删除文件|
|`sdk.file.save_current_file`|保存当前文件|
|`sdk.file.save_current_file_as`|另存为|
|`sdk.file.upload_selected_local_file_item`|上传选中的本地文件|

### 4.2 `IDE -> SDK`

|type|说明|
|---|---|
|`ide.event.callback`|用户交互事件回调|
|`ide.lifecycle.hook`|生命周期钩子|
|`ide.page.refresh`|触发 UI 刷新|
|`ide.request`|通用请求|
|`ide.response.path`|路径查询响应|

### 4.3 响应（双向）

|type|说明|
|---|---|
|`*.response.ok`|成功响应|
|`*.response.error`|错误响应|

---

## 5. 载荷模型（Payload）

每个 `type` 对应一个独立的 Pydantic 模型，通过 `type` 分发路由。

### 5.1 `sdk.page.push` —— 推送页面 UI

```python
class PagePayload(BaseModel):
    pages: Dict[str, str]   # key=页面名称, value=RFW 代码
```

```json
{
  "type": "sdk.page.push",
  "payload": {
    "pages": {
      "main": "import core.widgets; import core.material;\nScaffold(...);",
      "settings": "import core.widgets;\nText(\"Settings\");"
    }
  }
}
```

### 5.2 `sdk.var.set` —— 设置变量

```python
class VarSetPayload(BaseModel):
    name: str       # 变量路径，如 "data.counter"
    value: Any      # 任意 JSON 可序列化值
```

```json
{
  "type": "sdk.var.set",
  "payload": {
    "name": "data.counter",
    "value": 42
  }
}
```

### 5.3 `sdk.path.request` —— 请求路径

```python
class PathScope(str, Enum):
    ASSETS   = "assets"
    CACHE    = "cache"
    DATA     = "data"
    TEMP     = "temp"

class PathRequestPayload(BaseModel):
    scope: PathScope
```

```json
{
  "type": "sdk.path.request",
  "payload": {
    "scope": "assets"
  }
}
```

### 5.4 `ide.event.callback` —— 事件回调

```python
class EventCallbackPayload(BaseModel):
    page: str              # 事件所在页面
    name: str              # 事件名称 (对应 Page.events 的 key)
    args: Dict[str, Any]   # 回调参数
```

```json
{
  "type": "ide.event.callback",
  "payload": {
    "page": "main",
    "name": "on_submit",
    "args": {
      "value": "hello"
    }
  }
}
```

### 5.5 `ide.lifecycle.hook` —— 生命周期钩子

```python
class LifecycleHook(str, Enum):
    INSTALL   = "install"
    START     = "start"
    PAUSE     = "pause"
    RESUME    = "resume"
    DISPOSE   = "dispose"
    UNINSTALL = "uninstall"

class LifecyclePayload(BaseModel):
    hook: LifecycleHook
```

```json
{
  "type": "ide.lifecycle.hook",
  "payload": {
    "hook": "start"
  }
}
```

### 5.6 `ide.page.refresh` —— IDE 触发刷新

```python
class RefreshPayload(BaseModel):
    pass  # 无参数，仅触发
```

```json
{
  "type": "ide.page.refresh",
  "payload": {}
}
```

### 5.7 `*.response.ok` —— 成功响应

```python
class OkResponsePayload(BaseModel):
    data: Optional[Any] = None   # 响应数据
```

```json
{
  "type": "sdk.response.ok",
  "reply_to": "uuid",
  "payload": { "data": null }
}
```

### 5.8 `*.response.error` —— 错误响应

```python
class ErrorCode(str, Enum):
    KEY_NOT_FOUND    = "key_not_found"
    API_NOT_FOUND    = "api_not_found"
    INVALID_REQUEST  = "invalid_request"
    INTERNAL_ERROR   = "internal_error"
    TIMEOUT          = "timeout"

class ErrorResponsePayload(BaseModel):
    code: ErrorCode
    message: str
    details: Optional[Any] = None
```

```json
{
  "type": "ide.response.error",
  "reply_to": "req-uuid-xxx",
  "payload": {
    "code": "key_not_found",
    "message": "Page 'main' not found",
    "details": null
  }
}
```

### 5.9 `*.response.path` —— 路径响应

```python
class PathResponsePayload(BaseModel):
    scope: PathScope
    path: str
```

```json
{
  "type": "ide.response.path",
  "reply_to": "req-uuid-xxx",
  "payload": {
    "scope": "assets",
    "path": "/data/plugin/assets"
  }
}
```

---

## 6. 完整 Pydantic 模型

```python
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from enum import Enum
from uuid import uuid4
import time


# ─── 通用 ───────────────────────────────────────────

def new_id() -> str:
    return uuid4().hex

def now() -> int:
    return int(time.time() * 1000)


# ─── 辅助枚举 ──────────────────────────────────────

class PathScope(str, Enum):
    ASSETS = "assets"
    CACHE  = "cache"
    DATA   = "data"
    TEMP   = "temp"

class LifecycleHook(str, Enum):
    START     = "start"
    PAUSE     = "pause"
    RESUME    = "resume"
    DISPOSE   = "dispose"

class ErrorCode(str, Enum):
    KEY_NOT_FOUND    = "key_not_found"
    API_NOT_FOUND    = "api_not_found"
    INVALID_REQUEST  = "invalid_request"
    INTERNAL_ERROR   = "internal_error"
    TIMEOUT          = "timeout"


# ─── 载荷模型 ──────────────────────────────────────

class PagePayload(BaseModel):
    pages: Dict[str, str]

class VarSetPayload(BaseModel):
    name: str
    value: Any

class PathRequestPayload(BaseModel):
    scope: PathScope

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


# ─── 消息信封 ──────────────────────────────────────

class Envelope(BaseModel):
    version: str = "0.0"
    id: str = Field(default_factory=new_id)
    type: str
    payload: dict
    reply_to: Optional[str] = None
    timestamp: int = Field(default_factory=now)


# ─── 便捷构造 ──────────────────────────────────────

def request(type_: str, payload: BaseModel) -> Envelope:
    return Envelope(type=type_, payload=payload.dict())

def reply(original: Envelope, type_: str, payload: BaseModel) -> Envelope:
    return Envelope(type=type_, payload=payload.dict(), reply_to=original.id)

def ok(original: Envelope, data: Any = None) -> Envelope:
    return reply(original, f"{original.type.rsplit('.', 1)[0]}.response.ok",
                 OkResponsePayload(data=data))

def err(original: Envelope, code: ErrorCode, message: str,
        details: Any = None) -> Envelope:
    return reply(original, f"{original.type.rsplit('.', 1)[0]}.response.error",
                 ErrorResponsePayload(code=code, message=message, details=details))
```

---

## 7. 消息流

### 7.1 连接初始化

```
SDK                             IDE
 │                               │
 │ ── sdk.path.request ────────► │  scope: assets
 │                               │
 │ ◄── ide.response.path ─────── │  scope: assets, path: "/data/..."
 │                               │
 │ ── sdk.page.push ───────────► │  自动推送首屏 UI
```

### 7.2 事件回调

```
SDK                             IDE
 │                               │
 │ ◄── ide.event.callback ────── │  page: "main", name: "on_submit", args: {...}
 │                               │
 │ ── sdk.response.ok ─────────► │  (可选确认)
```

### 7.3 生命周期

```
SDK                             IDE
 │                               │
 │ ◄── ide.lifecycle.hook ────── │  hook: "start"
 │                               │
 │ ── sdk.response.ok ─────────► │  (可选确认)
```

### 7.4 变量推送

```
SDK                             IDE
 │                               │
 │ ── sdk.var.set ─────────────► │  name: "data.counter", value: 42
```

### 7.5 IDE 触发刷新

```
SDK                             IDE
 │                               │
 │ ◄── ide.page.refresh ──────── │
 │                               │
 │ ── sdk.page.push ───────────► │  重新推送所有页面
```

---

## 8. SERVER ↔ CLIENT 角色模型

| 维度           | SDK (Python)               | IDE (Dart/Flutter)         |
| -------------- | -------------------------- | -------------------------- |
| WebSocket 角色 | **Server**           | **Client**           |
| 监听地址       | `ws://localhost:{port}`  | 主动连接                   |
| 启动时机       | `Bridge.start()`         | IDE 检测端口后连接         |
| 生命周期发起   | 接收`ide.lifecycle.hook` | 发送`ide.lifecycle.hook` |

---
