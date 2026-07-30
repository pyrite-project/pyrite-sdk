# PyriteSDK API 参考手册

## 目录

1. [基础概念](#1-基础概念)
2. [Page 页面](#2-page-页面)
3. [UI 组件（Widgets）](#3-ui-组件widgets)
4. [语句（Sentences）](#4-语句sentences)
5. [事件系统](#5-事件系统)
6. [变量系统](#6-变量系统)
7. [组件树构建语法](#7-组件树构建语法)
8. [RFW 序列化](#8-rfw-序列化)
9. [IDE API](#9-ide-api)
10. [完整示例](#10-完整示例)

---

## 1. 基础概念

### 1.1 RFW（Remote Flutter Widgets）

SDK 使用 RFW 格式描述 UI。Python 代码构建组件树，序列化为 RFW 字符串后通过 WebSocket 推送给 IDE 渲染。

### 1.2 继承链

```
RFWSerializable (抽象基类)
├── ContextNode (上下文节点，支持 with 语句)
│   ├── Widget (UI 组件)
│   │   ├── Container, Column, Row, ...
│   │   ├── NewWidget (自定义组件)
│   │   └── Widget (引用已有组件)
│   └── Page (页面)
├── Event (事件)
├── Var (变量引用)
├── Match / Case (条件匹配)
├── ForLoop (循环)
└── DataSerializer (数据序列化)
```

### 1.3 导入约定

```python
# 组件
from pyrite_sdk.api.ui.widgets import *

# 页面
from pyrite_sdk.api.ui.page import Page

# 事件
from pyrite_sdk.api.ui.event import Event

# 语句（Var, Match, Case, ForLoop, let 等）
from pyrite_sdk.api.ui.sentence import *

# 模型与常量
from pyrite_sdk.models.schema import request, OkResponsePayload
from pyrite_sdk.models.consts import Package, Ui

# 插件基类
from pyrite_sdk.core.plugin import UiPlugin, ServicePlugin, DataPlugin
```

### 1.4 插件基类

| 类型 | 必须实现 | 说明 |
| --- | --- | --- |
| `UiPlugin` | `on_start()` | 提供 `pages`，并暴露 File、Board、Editor、Router、Persistence 和 Serial 等接口 |
| `ServicePlugin` | `on_start()` | 后台服务，不包含 `pages`、Editor 和 Router |
| `DataPlugin` | `on_contribute()` | 一次性贡献 Theme、I18n 或 Stubs；响应完成后自动停止 |

所有插件都提供 `bridge`、`path`、`settings`、`message`、`dialog`、`theme`、`i18n` 和 `stubs`。生命周期钩子 `on_pause()`、`on_resume()`、`on_refresh()`、`on_dispose()` 均有默认空实现。

---

## 2. Page 页面

`Page` 是组件树的根节点，管理页面依赖包、事件注册和 RFW 输出。

### 构造

```python
Page(packages: list[str])
```

| 参数 | 类型 | 说明 |
|------|------|------|
| `packages` | `list[str]` | 页面依赖的 RFW 包，如 `["core.widgets", "core.material"]` |

### 属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `packages` | `list[str]` | 依赖包列表 |
| `events` | `dict[str, Callable]` | 事件名 → 回调函数映射 |
| `children` | `list[ContextNode]` | 子组件列表 |

### 方法

| 方法 | 说明 |
|------|------|
| `to_rfw() -> str` | 序列化为 RFW 字符串 |
| `print_tree(indent, print_args)` | 打印组件树结构 |
| `add(child)` | 添加子组件 |
| `__enter__` / `__exit__` | 支持 `with` 上下文管理器 |

### 用法

```python
# 方式一：独立构建
page = Page(packages=[Package.core.widgets, Package.core.material])
root = NewWidget("root").add_to(page)
with Container().add_to(root):
    Text("Hello")

# 方式二：with 语句
page = Page(packages=[Package.core.widgets, Package.core.material])
with NewWidget("root").add_to(page):
    with Container():
        Text("Hello")
```

---

## 3. UI 组件（Widgets）

所有组件继承自 `Widget`，支持 `with` 上下文管理器嵌套子组件。

### 3.1 Container 容器

```python
Container(
    color=None,       # 背景色
    padding=None,     # 内边距
    margin=None,      # 外边距
    **kwargs          # 其他 Flutter Container 属性
)
```

**示例**:
```python
# 基础容器
Container(
    padding=[16.0, 16.0, 16.0, 16.0],
    margin=[8.0, 8.0, 8.0, 8.0]
)

# 带装饰
Container(
    decoration={"type": "box", "border": [{}]}
)

# 带背景色
Container(color="0xFF2196F3")
```

### 3.2 Column 垂直布局

```python
Column(
    padding=None,
    margin=None,
    **kwargs
)
```

支持多子组件。子组件按垂直方向排列。

```python
with Column():
    Text("第一行")
    Text("第二行")
    Text("第三行")
```

### 3.3 Row 水平布局

```python
Row(
    padding=None,
    margin=None,
    **kwargs
)
```

支持多子组件。子组件按水平方向排列。

```python
with Row():
    Text("左")
    Text("中")
    Text("右")
```

### 3.4 Center 居中

```python
Center(
    padding=None,
    margin=None,
    **kwargs
)
```

单子组件，将其子组件居中显示。

```python
with Center():
    Text("居中文本")
```

### 3.5 Expanded 弹性填充

```python
Expanded(flex=None, **kwargs)
```

在 `Row` 或 `Column` 中填充剩余空间。

```python
with Row():
    with Expanded():
        Text("填充空间")
    Text("固定宽度")
```

### 3.6 FittedBox 自适应

```python
FittedBox(fit=None, alignment=None, clip_behavior=None, **kwargs)
```

将其子组件缩放以适应可用空间。

### 3.6.1 常用布局与滚动组件

以下组件均继承 `Widget`，支持 `with` 嵌套和 `**kwargs` 透传：

| 组件 | 主要参数 | 说明 |
|------|----------|------|
| `Padding` | `padding` | 内边距容器 |
| `SizedBox` | `width`, `height` | 固定尺寸或空白间距 |
| `Align` | `alignment`, `width_factor`, `height_factor` | 对齐子组件 |
| `Flexible` | `flex`, `fit` | 弹性布局子项 |
| `Spacer` | `flex` | 弹性空白 |
| `Stack` | `alignment`, `fit`, `clip_behavior` | 多子组件叠放 |
| `Positioned` | `left`, `top`, `right`, `bottom`, `width`, `height` | `Stack` 内定位 |
| `SafeArea` | `left`, `top`, `right`, `bottom`, `minimum` | 避开系统安全区 |
| `SingleChildScrollView` | `scroll_direction`, `reverse`, `padding`, `primary` | 单子组件滚动 |
| `ListView` | `scroll_direction`, `reverse`, `padding`, `shrink_wrap` | 多子组件滚动列表 |
| `Wrap` | `direction`, `spacing`, `run_spacing` | 自动换行布局 |
| `Divider` | `height`, `thickness`, `indent`, `end_indent`, `color` | 分割线 |
| `Card` | `color`, `elevation`, `margin`, `shape` | Material 卡片 |

### 3.7 Text 文本

```python
Text(
    text: str | list | DataParser,  # 文本内容（支持变量拼接）
    style=None,                      # 文本样式
    text_direction=None,             # 文本方向
    text_align=None,
    soft_wrap=None,
    overflow=None,
    max_lines=None,
    semantics_label=None,
    **kwargs
)
```

**示例**:
```python
# 纯文本
Text("Hello World")

# 变量拼接（列表形式）
Text(["Hello, ", data.name])

# 带方向
Text("RTL 文本", text_direction=Ui.LTR)
```

### 3.8 按钮组件

```python
TextButton(
    on_pressed: Event = None,  # 点击事件
    on_long_press: Event = None,
    style=None,
    autofocus=None,
    **kwargs
)

ElevatedButton(on_pressed=None, on_long_press=None, style=None, autofocus=None, **kwargs)
OutlinedButton(on_pressed=None, on_long_press=None, style=None, autofocus=None, **kwargs)
FilledButton(on_pressed=None, on_long_press=None, on_hover=None, on_focus_change=None, style=None, autofocus=None, clip_behavior=None, **kwargs)
IconButton(
    icon,
    on_pressed=None,
    tooltip=None,
    icon_size=None,
    color=None,
    disabled_color=None,
    splash_radius=None,
    autofocus=None,
    on_long_press=None,
    on_hover=None,
    selected_icon=None,
    is_selected=None,
    visual_density=None,
    padding=None,
    alignment=None,
    focus_color=None,
    hover_color=None,
    highlight_color=None,
    splash_color=None,
    enable_feedback=None,
    constraints=None,
    **kwargs
)
FloatingActionButton(on_pressed=None, tooltip=None, background_color=None, mini=None, **kwargs)
```

**示例**:
```python
with TextButton(on_pressed=Event(on_click, args={"id": 0})):
    Text("点击我")
```

### 3.9 输入与选择组件

```python
TextField(
    decoration=None,
    keyboard_type=None,
    text_input_action=None,
    max_lines=None,
    enabled=None,
    read_only=None,
    on_changed=None,
    on_submitted=None,
    on_tap=None,
    **kwargs
)

Checkbox(value=None, on_changed=None, tristate=None, active_color=None, **kwargs)
Switch(value=None, on_changed=None, active_color=None, **kwargs)
RadioGroup(group_value="", on_changed=None, items=None, active_color=None, dense=None, **kwargs)
Slider(value=None, on_changed=None, min=None, max=None, divisions=None, label=None, on_change_start=None, on_change_end=None, **kwargs)
DropdownButton(items=None, value=None, on_changed=None, hint=None, disabled_hint=None, **kwargs)
DropdownItem(label, value=None, enabled=True)
```

`on_changed` 等回调参数可传 `Event`，也可传 `let(...)` 等 RFW 语句。

```python
DropdownButton(
    items=[
        DropdownItem("自动", "auto"),
        DropdownItem("高质量", "high"),
    ],
    value=data.quality,
    on_changed=Event(on_quality_changed),
)
```

`DropdownItem` 的 `label` 可以是字符串或组件；传入组件时必须同时提供 `value`。`value` 支持字符串、数字、布尔值或 `None`。

### 3.10 媒体与列表组件

```python
Icon(icon, size=None, color=None, semantic_label=None, **kwargs)
Image(
    source,
    source_type="file",
    width=None,
    height=None,
    scale=None,
    package=None,
    color=None,
    color_blend_mode=None,
    fit=None,
    alignment=None,
    repeat=None,
    semantic_label=None,
    exclude_from_semantics=None,
    filter_quality=None,
    gapless_playback=None,
    is_anti_alias=None,
    cache_width=None,
    cache_height=None,
    **kwargs
)
VideoPlayer(
    source,
    source_type="file",
    width=None,
    height=None,
    package=None,
    autoplay=False,
    looping=False,
    muted=False,
    show_controls=True,
    fit="contain",
    **kwargs
)
ListTile(leading=None, title=None, subtitle=None, trailing=None, on_tap=None, **kwargs)
Tooltip(message, padding=None, margin=None, prefer_below=None, on_triggered=None, **kwargs)
Chip(label, avatar=None, delete_icon=None, on_deleted=None, background_color=None, **kwargs)
ExpansionTile(title, leading=None, subtitle=None, on_expansion_changed=None, initially_expanded=None, **kwargs)
CircularProgressIndicator(value=None, background_color=None, color=None, stroke_width=None)
LinearProgressIndicator(value=None, background_color=None, color=None, min_height=None)
```

`Image` 和 `VideoPlayer` 的 `source_type` 支持 `"file"`、`"network"`。本地路径使用 `"file"`；网络 URL 使用 `"network"`。

```python
Image(
    "C:/media/cover.png",
    source_type="file",
    width=320,
    height=180,
    fit=BoxFit.cover,
)

VideoPlayer(
    "C:/media/demo.mp4",
    source_type="file",
    autoplay=True,
    looping=True,
    show_controls=True,
)

with Tooltip("播放视频"):
    Icon(Icons.play_arrow)

Chip(label=Text("Python"), on_deleted=Event(remove_tag))

with ExpansionTile(title=Text("高级选项"), initially_expanded=False):
    Text("选项内容")
```

当组件作为另一个组件的参数传入时，不会再被当前 `with` 上下文误挂载为兄弟节点。

### 3.11 GestureDetector 手势检测器

```python
GestureDetector(
    on_tap=None,           # 单击
    on_double_tap=None,    # 双击
    on_long_press=None,    # 长按
    on_tap_down=None,      # 手指按下
    on_tap_up=None,        # 手指抬起
    on_tap_cancel=None,    # 手势取消
    **kwargs
)
```

事件参数类型: `Event | DataSerializer | Var`

**示例**:
```python
GestureDetector(
    on_tap_down=let(state.down, True),
    on_tap_up=let(state.down, False),
    on_tap_cancel=let(state.down, False),
    on_tap=args.on_pressed
)
```

### 3.12 Scaffold 脚手架

```python
Scaffold(
    app_bar=None,
    floating_action_button=None,
    drawer=None,
    end_drawer=None,
    background_color=None,
    bottom_navigation_bar=None,
    resize_to_avoid_bottom_inset=None,
    **kwargs
)
```

子组件通过 `body` 键名挂载（与其他组件的 `children`/`child` 不同）。

```python
with Scaffold():
    with Container():  # 此容器挂载到 body
        Text("页面内容")
```

### 3.13 AppBar 应用栏

```python
AppBar(
    title=None,
    leading=None,
    actions=None,
    background_color=None,
    foreground_color=None,
    elevation=None,
    center_title=None,
    **kwargs
)
```

通常与 `Scaffold` 配合使用。

### 3.14 NewWidget 自定义组件定义

```python
NewWidget(
    name: str,                    # 组件名
    states: dict[str, Any] | None = None,  # 初始状态
    **kwargs
)
```

定义一个可复用的组件模板，输出格式为 `widget Name {state} = ...`。

**示例**:
```python
# 定义一个带状态的按钮组件
button = NewWidget("Button", states={"down": False}).add_to(page)
with GestureDetector(
    on_tap_down=let(state.down, True),
    on_tap_up=let(state.down, False)
).add_to(button):
    with Container(
        margin=Match(
            state.down,
            Case(False, [0.0, 0.0, 8.0, 8.0]),
            Case(True, [8.0, 8.0, 0.0, 0.0])
        )
    ):
        VarWidget(args.child)

# 使用自定义组件
root = NewWidget("root").add_to(page)
with Container().add_to(root):
    with Widget("Button", on_pressed=Event(on_click)):
        Text("按钮内容")
```

### 3.15 Widget 引用已有组件

```python
Widget(
    name: str,        # 要引用的组件名
    **kwargs          # 传递给组件的参数
)
```

引用 `NewWidget` 定义的组件，可传入事件、子组件等参数。

```python
with Widget("Button", on_pressed=Event(handler)):
    with TextButton():
        Text("按钮内容")
```

### 3.16 VarWidget 变量组件

```python
VarWidget(var: Var)
```

将变量直接渲染为 UI 节点。

```python
VarWidget(data.label)
VarWidget(args.child)
```

### 3.17 组件通用方法

| 方法 | 说明 |
|------|------|
| `add_to(parent) -> self` | 添加到父组件，返回自身 |
| `add(child) -> child` | 添加子组件 |
| `alias(name) -> self` | 设置子组件挂载的键名别名 |
| `to_rfw() -> str` | 序列化为 RFW 字符串 |
| `print_tree(indent, print_args)` | 打印组件树 |

### 3.18 组件子组件键名规则

| 组件 | 键名 | multi_child |
|------|------|-------------|
| `Column`, `Row` | `children` | true |
| `Scaffold` | `body` | false |
| 其他所有组件 | `child` | false |

可通过 `alias("custom_key")` 修改挂载键名。

---

## 4. 语句（Sentences）

### 4.1 Var 变量引用

```python
Var(*paths: str)
```

表示 RFW 中的变量路径，用 `.` 连接。

```python
data.counter      # Var("data", "counter")
args.on_pressed   # Var("args", "on_pressed")
state.down        # Var("state", "down")
```

**预定义变量**:

| 变量 | 含义 |
|------|------|
| `data` | 数据模型 `Var("data")` |
| `args` | 组件参数 `Var("args")` |
| `state` | 组件状态 `Var("state")` |

**属性访问链**:
```python
data.x           # "data.x"
data.user.name   # "data.user.name"
args.child       # "args.child"
```

### 4.2 let 赋值语句

```python
let(var: Var, value: Any) -> DataSerializer
```

生成 RFW 赋值语句 `set var = value`。

```python
let(state.down, True)          # "set state.down = true"
let(data.counter, 42)          # "set data.counter = 42"
let(data.name, "Pyrite")       # "set data.name = \"Pyrite\""
let(state.enabled, data.enabled == False)
```

### 4.3 Expr 表达式

`Var` 继承自 `Expr`。当前文本 RFW 库支持相等和比较条件，并将它们降低为 `switch`；不支持算术表达式或 `&&` / `||` 组合。

```python
data.kind == "fallback"
data.count > 0
~state.enabled
ternary(state.enabled, "on", "off")
Icons.person
EdgeInsets.all(8)
BoxDecoration(color=Colors.green, border_radius=BorderRadius.circular(8))
TextStyle(font_size=16, font_weight=FontWeight.bold)
```

支持的 helper:

| helper | 说明 |
|--------|------|
| `expr(value)` | 将值包装为 RFW 表达式 |
| `ref(*parts)` / `Ref` | 生成命名空间引用，如 `ref("Icons").person` |
| `call(name, *args, **kwargs)` | 生成 RFW 函数/构造调用，关键字参数会从 snake_case 转 camelCase |
| `ternary(condition, when_true, when_false)` | 生成三元条件表达式 |

常用命名空间已预置：`Icons`、`Colors`、`EdgeInsets`、`Alignment`、`Border`、`BorderRadius`、`BoxDecoration`、`Radius`、`TextStyle`、`FontWeight`、`FontStyle`、`MainAxisAlignment`、`CrossAxisAlignment`、`MainAxisSize`、`TextAlign`、`TextDirection`、`Axis`、`BoxFit`、`Clip`。

比较可用 Python 操作符 `==`、`!=`、`<`、`<=`、`>`、`>=`，也可使用 `eq()`、`ne()`、`lt()`、`le()`、`gt()`、`ge()`。数值范围比较只接受 0 到 100 的非负整数阈值，因为序列化器会展开 `switch` case。`~expr` / `not_()` 可反转布尔条件。`+`、`-`、`*`、`/`、`%`、`&`、`|` 以及 `and_()` / `or_()` 当前会抛出 `TypeError`。

### 4.4 Match / Case 条件匹配

```python
Match(var: Var, *cases: Case)
Case(cond: Any, value: Any)
```

生成 RFW `switch` 语句，根据变量值选择不同结果。

```python
# 基础用法
margin=Match(
    state.down,
    Case(False, [0.0, 0.0, 8.0, 8.0]),
    Case(True, [8.0, 8.0, 0.0, 0.0])
)

# 多条件
color=Match(
    data.status,
    Case("error", "0xFFF44336"),
    Case("warning", "0xFFFF9800"),
    Case("success", "0xFF4CAF50"),
    DefaultCase("0xFF000000")
)

# 嵌套使用
Text(
    Match(
        data.count,
        Case(0, "无数据"),
        Case(1, "一条数据"),
        DefaultCase("多条数据")
    )
)
```

**RFW 输出**:
```
switch state.down { false: [0, 0, 8, 8], true: [8, 8, 0, 0] }
```

### 4.5 ForLoop 循环

```python
ForLoop(var: str, in_list: Var | RFWSerializable | str, *widgets: WidgetType)
```

生成 RFW `for` 循环语句。

```python
# 构造参数写法
ForLoop(
    "item",
    data.items,
    Text(["- ", Var("item").label])
)

# with 嵌套写法
with Column():
    with ForLoop("item", data.items):
        Text(["- ", Var("item").label])
```

**RFW 输出**:
```
...for item in data.items:
  Text(text: ["- ", item.label]),
```

---

## 5. 事件系统

### 5.1 Event 事件

```python
Event(
    callback: Callable,      # 回调函数
    args: dict[str, Any] | None = None,  # 传递给回调的参数，默认 {}
    event: str = ""          # 事件名（可选，自动生成）
)
```

**回调签名**: `def handler(**kwargs)`

```python
def on_click(**kwargs):
    print("Clicked!", kwargs)

# 绑定事件
button = TextButton(on_pressed=Event(on_click, args={"id": 0}))

# 内联 lambda
button = TextButton(on_pressed=Event(lambda **kw: print(kw)))
```

### 5.2 事件注册流程

1. `Event` 对象通过组件参数传入
2. `Widget.setup()` 调用 `setup_event(event)`
3. `event.events` 指向 `Page.events` 字典
4. `event.setup()` 将回调注册到 `Page.events[event_name]`
5. `event.to_rfw()` 输出 `event "event_name" {args}`

### 5.3 事件回调处理（IDE → SDK）

IDE 发送 `ide.event.callback` 消息：
```json
{
  "type": "ide.event.callback",
  "payload": {
    "page": "home",
    "name": "event_0",
    "args": {"id": 0, "value": "hello"}
  }
}
```

Bridge 通过 `page.events[name](**args)` 调用对应的回调函数。

### 5.4 事件结合 let

```python
# 手势事件中使用 let 修改状态
GestureDetector(
    on_tap_down=let(state.down, True),
    on_tap_up=let(state.down, False),
    on_tap=Event(on_click, args={"id": 0})
)

# 通过 Bridge.let() 运行时修改变量
def on_click(**kwargs):
    plugin.bridge.let(data.counter, 42)
    plugin.bridge.let(data.name, "Hello")
```

---

## 6. 变量系统

### 6.1 变量引用（Var）

`Var` 表示 RFW 中的响应式变量路径。

```python
data.x         # "data.x"
data.user.name # "data.user.name"
state.count    # "state.count"
args.child     # "args.child"
```

### 6.2 变量辅助函数

```python
data_("x")           # "$[data.x]"    - 内联变量引用
args_("on_pressed")  # "$[args.on_pressed]"
state_("down")       # "$[state.down]"
```

`$[...]` 语法用于在字符串中嵌入变量，如 `Text(["Hello, ", data.name])`。

### 6.3 Bridge.let() 运行时变量设置

```python
plugin.bridge.let(var: Var, value: Any)
```

通过 WebSocket 发送 `sdk.var.set` 消息，实时更新 IDE 中的变量值。

**前缀自动剥离**: `let()` 会自动去除变量路径中的 `data`/`args`/`state` 前缀，仅发送剩余部分。例如：

| 调用 | 实际发送的 name |
|------|----------------|
| `let(data.x, 42)` | `"x"` |
| `let(state.down, True)` | `"down"` |
| `let(args.child, "text")` | `"child"` |
| `let(data.user.name, "hi")` | `"user.name"` |

```python
# 在回调中更新 UI
def on_submit(**kwargs):
    plugin.bridge.let(data.result, "提交成功")
    plugin.bridge.let(data.counter, data.counter + 1)
```

### 6.4 数据类型支持

| Python 类型 | RFW 序列化 |
|-------------|-----------|
| `str` | `"string"` |
| `int` / `float` | `42` / `3.14` |
| `bool` | `true` / `false` |
| `None` | `null` |
| `list` | `[1, 2, 3]` |
| `dict` | `{"key": "value"}` |
| `Enum` | 序列化其 `.value` |
| `Var` / `Expr` | `data.x` / `switch data.kind { "ok": true, default: false }` |
| `RFWSerializable` | 调用 `to_rfw()` |

---

## 7. 组件树构建语法

### 7.1 with 语句嵌套

```python
root = NewWidget("root").add_to(page)
with Container().add_to(root):
    with Column():
        Text("标题")
        with Row():
            Text("左")
            Text("右")
```

**规则**: `with` 退出时，内部的子组件自动挂载到外部组件。

### 7.2 add_to 显式挂载

```python
root = NewWidget("root").add_to(page)
container = Container().add_to(root)
column = Column().add_to(container)
text = Text("内容").add_to(column)
```

### 7.3 add 多子组件

```python
column = Column()
column.add(Text("第一行"), Text("第二行"), Text("第三行"))
```

### 7.4 alias 键名别名

```python
# 默认子组件挂载到 "child"
with Container():
    Text("默认")

# 通过 alias 修改挂载键名
with Container().alias("header"):
    Text("挂载到 header 键")

# Scaffold 默认挂载到 "body"
with Scaffold():
    with Container():  # 自动挂载到 body
        Text("内容")
```

### 7.5 自定义组件 + 引用

```python
# 1. 定义组件
button = NewWidget("MyButton", states={"pressed": False}).add_to(page)
with GestureDetector(
    on_tap_down=let(state.pressed, True),
    on_tap_up=let(state.pressed, False)
).add_to(button):
    with Container(
        margin=Match(
            state.pressed,
            Case(False, [0.0, 0.0, 4.0, 4.0]),
            Case(True, [4.0, 4.0, 0.0, 0.0])
        )
    ):
        VarWidget(args.child)

# 2. 使用组件
root = NewWidget("root").add_to(page)
with Container().add_to(root):
    with Widget("MyButton", on_pressed=Event(handler)):
        Text("按钮文字")
```

### 7.6 Text 变量拼接

```python
# 纯文本
Text("Hello")

# 变量拼接（列表形式，自动合并相邻字符串字面量）
Text(["Hello, ", data.name, "!"])

# 混合静态和变量
Text(["计数: ", data.count, " 条"])
```

### 7.7 事件绑定到各组件

```python
# TextButton
TextButton(on_pressed=Event(handler, args={}))

# GestureDetector
GestureDetector(
    on_tap=Event(handler),
    on_long_press=Event(handler),
    on_tap_down=let(state.down, True)
)

# 自定义组件
Widget("Button", on_pressed=Event(handler))

# 任意组件通过 kwargs
Container(on_tap=Event(handler))
```

---

## 8. RFW 序列化

### 8.1 组件输出格式

```
组件名(参数名: 值, 参数名: 值)
```

```python
# Text("Hello")
Text(text: "Hello")

# Container(padding: [16, 16, 16, 16])
Container(padding: [16, 16, 16, 16])
```

### 8.2 自定义组件输出格式

```
widget 组件名 {初始状态} = 组件定义
```

```
widget Button {"down": false} = GestureDetector(onTap: event "event_0" {"id": 0}, child: Container(...))
```

### 8.3 Page 完整输出

```python
page.to_rfw()
# 输出:
# import core.widgets;import core.material;
# widget Button {"down": false} = GestureDetector(...);
# root(...) = Container(child: Column(children: [...]));
```

### 8.4 DataSerializer 序列化规则

| 输入 | 输出 |
|------|------|
| `"hello"` | `"hello"` |
| `42` | `42` |
| `3.14` | `3.14` |
| `True` | `true` |
| `False` | `false` |
| `None` | `null` |
| `[1, 2]` | `[1, 2]` |
| `{"k": "v"}` | `{"k": "v"}` |
| `Var("data", "x")` | `data.x` |
| `data.count + 1` | `(data.count + 1)` |
| `Event(...)` | `event "name" {args}` |
| `DataSerializer(..., serialize=False)` | 不加引号的原始值 |

---

## 9. IDE API

IDE API 方法分为两类：调用 `push_wait_response()` 的方法接受可选 `callback`，响应以关键字参数传入；调用 `push()` 的方法只负责发送。所需权限见 [IDE 命令与权限](ide_api.md)。

### 9.1 File

`UiPlugin.file` 和 `ServicePlugin.file` 操作本地工作区。

| 方法 | 说明 |
| --- | --- |
| `get_root_dir(callback=None)` | 获取工作区根目录 |
| `get_file_list(path, callback=None)` | 获取目录列表；`path` 使用 Envelope 的 `data` 字段 |
| `read_file(path, callback=None)` / `write_file(path, content, callback=None)` | 读写文件 |
| `exists(path, callback=None)` / `is_file(...)` / `is_directory(...)` | 查询路径 |
| `get_focus_file_node(callback=None)` / `get_focus_folder_node(...)` | 获取当前聚焦节点 |
| `get_unique_name(name, is_folder=False, callback=None)` | 请求不冲突的名称 |
| `create_file(path, callback=None)` / `create_folder(path, callback=None)` | 使用完整路径创建项目 |
| `copy_file(src, dst, callback=None)` / `move_file(...)` | 复制或移动文件 |
| `upload_file(local_path, board_path, callback=None)` | 上传本地文件到 Board |
| `rename(path, new_name)` / `delete(path)` | 重命名或删除，不等待响应 |
| `open_file(path)` / `open_folder(path)` | 在 IDE 中打开路径，不等待响应 |
| `save_current_file()` / `save_current_file_as()` | 保存或另存当前文件 |
| `upload_selected_local_file_item()` | 上传当前选择项 |

```python
plugin.file.create_file(
    "/workspace/test.txt",
    callback=lambda **response: print(response),
)
```

### 9.2 Board

`UiPlugin.board` 和 `ServicePlugin.board` 操作 Board 工作区。

| 方法 | 说明 |
| --- | --- |
| `get_root_dir(callback=None)` / `get_dir_list(path, callback=None)` | 获取根目录或目录列表 |
| `read_file(path, callback=None)` / `write_file(path, content, callback=None)` | 读写 Board 文件 |
| `exists(path, callback=None)` / `is_file(...)` / `is_directory(...)` | 查询路径 |
| `get_focus_file_node(callback=None)` / `get_focus_folder_node(...)` | 获取当前聚焦节点 |
| `get_corresponding_file_path(path, callback=None)` | 获取 Board 路径对应的本地路径 |
| `download_file(board_path, local_path, callback=None)` | 下载到本地路径 |
| `open_file(path)` / `download_selected_board_item()` | 打开或下载当前选择项 |
| `rename(path, new_name)` / `delete_file(path)` / `delete_folder(path)` | 修改 Board 项目 |

### 9.3 Editor 与 Router

`UiPlugin.editor` 提供以下方法族：

| 分类 | 方法 |
| --- | --- |
| 文本 | `get_text`, `set_text`, `get_line_count`, `get_line_text`, `get_selected_text`, `insert_text`, `replace_range`, `clear` |
| 光标与选择 | `get_cursor_position`, `set_cursor_position`, `get_selection`, `set_selection`, `select_all`, `go_to_line` |
| 剪贴板与历史 | `copy`, `cut`, `paste`, `undo`, `redo`, `can_undo`, `can_redo` |
| 搜索 | `find`, `find_regex`, `clear_search` |
| 标签页 | `open_file`, `close_tab`, `get_current_tab`, `list_tabs` |
| 装饰 | `set_ghost_text`, `clear_ghost_text`, `scroll_to_line` |

这些方法均接受可选 `callback`。`find(word, match_case=False, whole_word=False, callback=None)` 和 `find_regex(pattern, callback=None)` 的参数不可互换。

`UiPlugin.router` 在插件内部页面间导航：

```python
plugin.router.push("settings")
plugin.router.pop()
plugin.router.replace("details")
plugin.router.goto("home")
```

`current` 返回当前页，`stack` 返回历史栈副本。IDE 可通过 `ide.router.sync` 同步这两个值。

### 9.4 Persistence

`UiPlugin.persistence` 和 `ServicePlugin.persistence` 按 `group` / `key` 保存 JSON 可序列化值。

```python
plugin.persistence.get(group, key, callback=None)
plugin.persistence.set(group, key, value, callback=None)
plugin.persistence.delete(group, key, callback=None)
plugin.persistence.list_groups(callback=None)
plugin.persistence.list_keys(group, callback=None)
plugin.persistence.clear(group, callback=None)
```

### 9.5 Path、Dialog 与 Message

所有插件都有这些通用接口：

| 接口 | 方法 |
| --- | --- |
| `plugin.path` | `get(scope, callback=None)`；同步快捷方法 `plugin()`、`data()`、`cache()`、`temp()` 返回 `pathlib.Path` |
| `plugin.dialog` | `open_folder(title=None, initial_directory=None, callback=None)` |
| `plugin.message` | `show(message, type="info", callback=None)`；快捷方法 `info`、`success`、`warning`、`error` |

路径快捷方法会优先读取 IDE 注入的环境变量，否则等待 `ide.response.path`，默认超时 5 秒。

### 9.6 Serial

`UiPlugin.serial` 和 `ServicePlugin.serial` 提供：

```python
plugin.serial.list_ports(callback=None)
plugin.serial.get_status(callback=None)
plugin.serial.connect(port, callback=None)
plugin.serial.disconnect(callback=None)
plugin.serial.send(data, callback=None)
plugin.serial.send_command(command, chunked=True, callback=None)
plugin.serial.read(timeout_ms=1000, max_bytes=None, callback=None)
plugin.serial.run_python(code, timeout_ms=20000, callback=None)
plugin.serial.hardware_reset(callback=None)
plugin.serial.set_baud_rate(value, callback=None)
plugin.serial.set_auto_reconnect(value, callback=None)
```

`send()` 接受字符串、`bytes` 或整数序列；`bytes` 会序列化为整数列表。`hardware_reset()` 使用 IDE 当前选择的硬件复位策略；未连接或复位方式设为关闭时返回错误。`get_status()` 还会返回 `hardware_reset_strategy` 和 `hardware_reset_enabled`。

### 9.7 Settings

`plugin.settings.get(name, callback=None)`、`set(name, value, callback=None)` 和 `list(callback=None)` 是底层通用接口。还提供以下分组封装：

| 属性 | 类 | 范围 |
| --- | --- | --- |
| `settings.theme` | `ThemeSettings` | 主题模式、风格、颜色、插件主题和 Material 右键菜单 |
| `settings.editor` | `EditorSettings` | 字体、换行、缩进、建议、缩略图等编辑器配置 |
| `settings.lsp` | `LspSettings` | LSP 传输、诊断和语言能力开关 |
| `settings.serial` | `SerialSettings` | 波特率、自动重连、REPL、文件传输和硬件复位 |
| `settings.terminal` | `TerminalSettings` | 字体、字号和行高 |
| `settings.micropython` | `MicroPythonStubsSettings` | 存根开关、层和额外路径 |

ThemeSettings 的值约定：

| 方法 | 值 |
| --- | --- |
| `get_mode` / `set_mode` | `"system"`、`"light"` 或 `"dark"` |
| `get_style` / `set_style` | `"standard"`、`"compact"` 或 `"comfortable"` |
| `get_color` / `set_color` | ARGB32 `int`；`None` 表示使用系统动态颜色 |
| `get_active_plugin_theme_id` / `set_active_plugin_theme_id` | `"plugin_id::theme_name"`；`None` 表示内置主题 |
| `get_use_material_context_menu` / `set_use_material_context_menu` | `bool` |

SerialSettings 的新增值约定：

| 方法 | 值 |
| --- | --- |
| `get_repl_mode` / `set_repl_mode` | `"rawRepl"` 或 `"paste"` |
| `get_file_transfer_mode` / `set_file_transfer_mode` | `"streaming"` 或 `"chunked"` |
| `get_hardware_reset_strategy` / `set_hardware_reset_strategy` | `"disabled"`、`"dtrPulse"`、`"rtsPulse"` 或 `"esp32"` |

文件传输模式是偏好值；REPL 模式为 `paste` 时，IDE 始终使用分块传输。

```python
plugin.settings.theme.get_mode(callback=lambda **response: print(response))
plugin.settings.theme.set_color(0xFF008080)
plugin.settings.serial.set_repl_mode("rawRepl")
plugin.settings.serial.set_hardware_reset_strategy("esp32")
```

设置读取回调收到 `data={"name": ..., "value": ...}`；设置成功时收到 `data=True`。

### 9.8 Theme、I18n 与 Stubs

所有插件均可访问数据接口，`DataPlugin` 主要使用这些接口实现 `on_contribute()`。

| 接口 | 方法 |
| --- | --- |
| `plugin.theme` | `contribute(name, data)`, `register_runtime(name, data)`, `revoke(name)`, `get(name)`, `list()` |
| `plugin.i18n` | `contribute(locale, messages)`, `register_runtime(locale, messages)`, `revoke(locale)`, `get(locale)`, `list()` |
| `plugin.stubs` | `contribute(provider_id, profiles, ...)`, `register_runtime(...)`, `revoke(provider_id)`, `get(provider_id)`, `list()`, `resolve_layers(layers)` |

每个方法最后都接受可选 `callback`。`contribute` 用于插件声明式贡献；`register_runtime` 用于运行期注册。

---

## 10. 完整示例

### 10.1 基础页面

```python
from pyrite_sdk.api.ui.widgets import *
from pyrite_sdk.api.ui.page import Page
from pyrite_sdk.api.ui.event import Event
from pyrite_sdk.api.ui.sentence import *
from pyrite_sdk.models.consts import Package
from pyrite_sdk.core.plugin import UiPlugin

page = Page(packages=[Package.core.widgets, Package.core.material])

root = NewWidget("root").add_to(page)
with Container().add_to(root):
    with Column():
        Text("Hello, PyriteSDK!")
        with TextButton(on_pressed=Event(lambda **kw: print("clicked"))):
            Text("Click Me")

class MyPlugin(UiPlugin):
    def __init__(self):
        super().__init__()
        self.pages = {"home": page}
    def on_start(self): pass
    def on_dispose(self): pass

MyPlugin().start()
```

### 10.2 带状态的自定义按钮

```python
page = Page(packages=[Package.core.widgets, Package.core.material])

button = NewWidget("Button", states={"down": False}).add_to(page)
with GestureDetector(
    on_tap_down=let(state.down, True),
    on_tap_up=let(state.down, False),
    on_tap_cancel=let(state.down, False),
    on_tap=args.on_pressed
).add_to(button):
    with Container(
        margin=Match(
            state.down,
            Case(False, [0.0, 0.0, 8.0, 8.0]),
            Case(True, [8.0, 8.0, 0.0, 0.0])
        ),
        decoration={"type": "box", "border": [{}]}
    ):
        VarWidget(args.child)

root = NewWidget("root").add_to(page)
with Container().add_to(root):
    with Column():
        Text(["Hello, ", data.x])
        with TextButton(on_pressed=Event(lambda **kw: print("clicked"))):
            Text(["Hello, ", data.x])
        with Widget("Button", on_pressed=Event(handler, args={"id": 0})):
            with TextButton():
                Text(["Hello, ", data.x])
```

### 10.3 工作区操作

```python
def on_get_root(**kw):
    print("Root dir:", kw)
    plugin.bridge.let(data.root_dir, str(kw))

def on_get_files(**kw):
    print("Files:", kw)
    plugin.bridge.let(data.files, str(kw))

root = NewWidget("root").add_to(page)
with Container().add_to(root):
    with Column():
        with Widget("Button", on_pressed=Event(
            lambda **kw: plugin.file.get_root_dir(
                callback=lambda **cb: plugin.bridge.let(data.r0, str(cb))
            )
        )):
            with TextButton():
                Text("Get Root Dir")
        Text(["Root: ", data.r0])

        with Widget("Button", on_pressed=Event(
            lambda **kw: plugin.file.get_file_list(
                "/",
                callback=lambda **cb: plugin.bridge.let(data.r1, str(cb))
            )
        )):
            with TextButton():
                Text("Get File List")
        Text(["Files: ", data.r1])
```
