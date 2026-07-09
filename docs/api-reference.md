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
9. [工作区 API](#9-工作区-api)
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
from pyrite_sdk.core.plugin import Plugin
```

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
IconButton(icon, on_pressed=None, tooltip=None, icon_size=None, color=None, **kwargs)
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
```

`on_changed` 等回调参数可传 `Event`，也可传 `let(...)` 等 RFW 语句。

### 3.10 媒体与列表组件

```python
Icon(icon, size=None, color=None, semantic_label=None, **kwargs)
Image(image, width=None, height=None, fit=None, alignment=None, **kwargs)
ListTile(leading=None, title=None, subtitle=None, trailing=None, on_tap=None, **kwargs)
CircularProgressIndicator(value=None, background_color=None, color=None, stroke_width=None)
LinearProgressIndicator(value=None, background_color=None, color=None, min_height=None)
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
let(state.next_count, data.counter + 1)
```

### 4.3 Expr 表达式

`Var` 继承自 `Expr`，可直接组合 RFW 表达式，避免手写 `raw()` 字符串。

```python
data.counter + 1              # "(data.counter + 1)"
data.count > 0                # "(data.count > 0)"
(data.count > 0) & state.enabled
(data.kind == "fallback") | ~state.enabled
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

比较可用 Python 操作符：`==`、`!=`、`<`、`<=`、`>`、`>=`。布尔组合使用 `&`、`|`、`~`，也保留方法形式：`eq()`、`ne()`、`lt()`、`le()`、`gt()`、`ge()`、`and_()`、`or_()`、`not_()`。不要用 Python 的 `and` / `or`，因为它们会在 Python 运行期求值。

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
| `Var` / `Expr` | `data.x` / `(data.count + 1)` |
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

## 9. 工作区 API

### 9.1 File

通过 `plugin.file` 访问。

| 方法 | 参数 | 说明 |
|------|------|------|
| `get_root_dir(callback)` | `callback(**kwargs)` | 获取根目录路径 |
| `get_file_list(path, callback)` | `path: str, callback(**kwargs)` | 获取目录下文件列表（path 通过 `data` 字段传递） |
| `get_focus_file_node(callback)` | `callback(**kwargs)` | 获取当前聚焦的文件节点 |
| `get_focus_folder_node(callback)` | `callback(**kwargs)` | 获取当前聚焦的文件夹节点 |
| `create_file(name, parent_path, callback)` | `name?: str, parent_path?: str, callback?` | 创建文件 |
| `create_folder(name, parent_path, callback)` | `name?: str, parent_path?: str, callback?` | 创建文件夹 |
| `open_file(path)` | `path: str` | 打开文件 |
| `open_folder(path)` | `path: str` | 打开文件夹 |
| `rename_file(path, new_name)` | `path: str, new_name: str` | 重命名文件 |
| `delete_file(path)` | `path: str` | 删除文件 |
| `save_current_file()` | 无 | 保存当前文件 |
| `save_current_file_as()` | 无 | 另存为 |
| `upload_selected_local_file_item()` | 无 | 上传选中的文件 |

> **注意**: `get_file_list` 的 `path` 参数通过 Envelope 的 `data` 字段传递，而非 `payload`。其他带 `payload` 的方法使用对应的 Pydantic 模型序列化。

### 9.2 Board

通过 `plugin.board` 访问。当前为占位实现，暂无可用方法。

### 9.3 Dialog

通过 `plugin.dialog` 访问。

| 方法 | 参数 | 说明 |
|------|------|------|
| `open_folder(title=None, initial_directory=None, callback=None)` | `title?: str, initial_directory?: str, callback(**kwargs)` | 打开系统文件夹选择器，回调的 `data` 为选中的目录路径，取消时为 `None` |

**回调格式**: `callback(**kwargs)` — kwargs 包含 IDE 返回的数据。

```python
# 获取根目录
plugin.file.get_root_dir(
    callback=lambda **kw: print("Root:", kw)
)

# 获取文件列表
plugin.file.get_file_list(
    "/src",
    callback=lambda **kw: print("Files:", kw)
)

# 创建文件
plugin.file.create_file(
    name="test.txt",
    callback=lambda **kw: print("Created:", kw)
)
```

---

## 10. 完整示例

### 10.1 基础页面

```python
from pyrite_sdk.api.ui.widgets import *
from pyrite_sdk.api.ui.page import Page
from pyrite_sdk.api.ui.event import Event
from pyrite_sdk.api.ui.sentence import *
from pyrite_sdk.models.consts import Package
from pyrite_sdk.core.plugin import Plugin

page = Page(packages=[Package.core.widgets, Package.core.material])

root = NewWidget("root").add_to(page)
with Container().add_to(root):
    with Column():
        Text("Hello, PyriteSDK!")
        with TextButton(on_pressed=Event(lambda **kw: print("clicked"))):
            Text("Click Me")

class MyPlugin(Plugin):
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
