# PyriteSDK WebSocket 协议

本文档描述当前 `pyrite_sdk.models.schema` 和 `pyrite_sdk.core.bridge` 的实际行为。IDE 命令及权限另见 [IDE 命令与权限](ide_api.md)。

## 传输角色

| 项目 | 当前实现 |
| --- | --- |
| SDK | WebSocket Server |
| IDE | WebSocket Client |
| 地址 | `ws://localhost:{PYRITE_IDE_PLUGIN_PORT}` |
| 编码 | UTF-8 JSON 文本帧 |
| Server 监听地址 | `localhost` |

`Bridge.start()` 创建事件循环和有界消息队列，然后开始监听。队列大小由插件构造参数 `queue_size` 控制，默认 50。

## Envelope

所有消息使用同一个信封：

```python
class Envelope(BaseModel):
    version: str = "0.0"
    id: str                       # 默认 uuid4().hex
    type: str
    payload: dict
    data: Optional[Any] = None
    reply_to: Optional[str] = None
    timestamp: int                # Unix 毫秒时间戳
```

`request(type_, payload=None, data=None)` 创建普通请求。Pydantic payload 会先调用 `.dict()`；字典直接使用；没有 payload 时为 `{}`。

```json
{
  "version": "0.0",
  "id": "f57dc0de0cc048a49a112f1d7184ee20",
  "type": "sdk.file.read_file",
  "payload": {"path": "/workspace/main.py"},
  "data": null,
  "reply_to": null,
  "timestamp": 1784250000000
}
```

当前协议没有单独的版本协商握手；`version` 固定默认为 `0.0`。

## 消息方向

### SDK 到 IDE

SDK 发送的业务命令包括：

| 命名空间 | 用途 |
| --- | --- |
| `sdk.page.*`, `sdk.var.*`, `sdk.callback.*`, `sdk.router.*` | 页面、响应式数据、回调声明和内部路由 |
| `sdk.file.*`, `sdk.board.*`, `sdk.editor.*` | 本地工作区、Board 和编辑器操作 |
| `sdk.persistence.*`, `sdk.settings.*` | 插件持久化与 IDE 设置 |
| `sdk.serial.*` | 串口查询、连接、收发和 MicroPython 执行 |
| `sdk.theme.*`, `sdk.i18n.*`, `sdk.stubs.*` | 数据贡献、注册、查询和撤销 |
| `sdk.path.request` | 请求插件、资源、数据、缓存或临时目录 |
| `sdk.dialog.open_folder`, `sdk.message.show` | 系统文件夹选择器和 IDE 消息提示 |
| `sdk.output.append` | 转发插件标准输出或错误输出 |

完整命令与权限表见 [IDE 命令与权限](ide_api.md)。

### IDE 到 SDK

Bridge 当前直接处理以下消息：

| 消息 | Payload | 行为 |
| --- | --- | --- |
| `ide.page.refresh` | `{}` | 清理回调绑定，调用 `plugin.on_refresh()`，重新推送回调与页面，然后回复成功 |
| `ide.event.callback` | `{page, name, args}` | 查找 `Page.events[name]` 并以 `event(**args)` 调用 |
| `ide.lifecycle.hook` | `{hook}` | 分发 `start`、`pause`、`resume`、`dispose` |
| `ide.response.path` | `{scope, path}` | 设置资产路径或唤醒同步路径请求 |
| `ide.router.sync` | `{page, stack}` | 同步 `UiPlugin.router` 的当前页和历史栈 |

`LifecycleHook` 枚举还定义了 `install` 和 `uninstall`，但 Bridge 的生命周期分发表当前未给这两个值注册处理器；收到时会返回 `api_not_found`。

## 响应关联

需要响应的 SDK API 调用 `Bridge.push_wait_response()`：

1. 记录请求 `id` 与回调函数。
2. 将请求加入发送队列。
3. IDE 响应时将原请求 ID 写入 `reply_to`。
4. Bridge 用 `reply_to` 取出并删除回调。
5. 若响应 `payload` 是字典，执行 `callback(**payload)`；否则执行 `callback(payload)`。

`payload` 为空时 Bridge 会回退到旧式 `data` 字段。即使调用方没有传回调，SDK 也会注册一个空回调来正确消费响应。

成功和失败响应的标准构造如下：

```json
{
  "type": "sdk.response.ok",
  "payload": {"data": true},
  "reply_to": "original-request-id"
}
```

```json
{
  "type": "ide.response.error",
  "payload": {
    "code": "key_not_found",
    "message": "Page 'home' not found",
    "details": null
  },
  "reply_to": "original-request-id"
}
```

标准错误码是 `key_not_found`、`api_not_found`、`invalid_request`、`internal_error` 和 `timeout`。具体 IDE API 可能有命令专用的成功数据形状；例如设置读取返回 `data={"name": ..., "value": ...}`。

## 页面刷新与回调

UI 刷新按以下顺序执行：

1. 发送 `sdk.callback.clear`，清除 SDK 和 IDE 中的旧变量绑定。
2. 将 `Widget.next_widget_id` 归零。
3. 默认调用 `plugin.on_refresh()`。
4. 为自动绑定的输入组件恢复初始变量值，并发送 `sdk.callback.register`。
5. 收集所有 `Page.events` 名称并发送 `sdk.callback.set`。
6. 将 `{页面名: RFW 字符串}` 作为 `sdk.page.push` 发送。

自动变量绑定事件名使用 `callback_<widget_id>_<event>`。普通 `Event` 若未显式指定名称，则在组件 setup 时生成 `callback-<widget_id>-<event>`。两者的连字符格式不同，属于当前协议约定。

`ide.event.callback` 的载荷为：

```python
class EventCallbackPayload(BaseModel):
    page: str
    name: str
    args: dict[str, Any]
```

找不到页面或事件时返回 `key_not_found`；用户回调抛出异常时返回 `internal_error`。变量绑定事件没有 Python 回调函数，Bridge 识别到已注册的绑定名后直接返回成功。

## 路径请求

路径范围定义为：

| Scope | 快捷方法 |
| --- | --- |
| `plugin` | `plugin.path.plugin()` |
| `data` | `plugin.path.data()` |
| `cache` | `plugin.path.cache()` |
| `temp` | `plugin.path.temp()` |

请求：

```json
{
  "type": "sdk.path.request",
  "payload": {"scope": "data"}
}
```

响应：

```json
{
  "type": "ide.response.path",
  "payload": {
    "scope": "data",
    "path": "/path/to/plugin-data",
    "plugin_id": "optional-routing-id"
  }
}
```

`plugin_id` 不是 `PathResponsePayload` 的声明字段，但 IDE 可带上它供 Bridge 过滤其他插件的路径响应。快捷方法优先读取 `PYRITE_IDE_PLUGIN_DIR`、`PYRITE_IDE_PLUGIN_DATA_DIR`、`PYRITE_IDE_PLUGIN_CACHE_DIR`、`PYRITE_IDE_PLUGIN_TEMP_DIR`，否则同步等待响应，默认超时 5 秒。

## 输出转发

Bridge 启动时会安装标准输出路由。插件线程中的 `stdout` / `stderr` 按行转换为：

```json
{
  "type": "sdk.output.append",
  "payload": {
    "plugin_id": "my-plugin",
    "stream": "stdout",
    "text": "started"
  }
}
```

在事件循环建立前产生的输出会暂存，Bridge 初始化完成后再发送。由插件线程派生的 Python 线程会继承当前 Bridge 路由。

## 连接时序

```text
Plugin.start()
  -> SDK 监听 localhost:$PYRITE_IDE_PLUGIN_PORT
  -> IDE 连接
  -> SDK refresh()
  -> sdk.callback.clear / register / set
  -> sdk.page.push
  <- IDE lifecycle、事件、刷新、路由同步或 API 响应
```
