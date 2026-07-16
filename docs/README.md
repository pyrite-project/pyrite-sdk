# PyriteSDK 项目文档

## 1. 项目概述

**PyriteSDK** 是一个用于扩展 PyriteIDE 的 Python SDK。它允许开发者通过编写 Python 插件来为 PyriteIDE 添加自定义 UI 页面、处理用户交互事件、管理工作区文件，并将插件打包为可部署的资产。

- **项目名称**: pyrite-sdk
- **版本**: 0.0.0
- **许可证**: GNU AGPL v3
- **Python 要求**: >= 3.10
- **作者**: Can1425, kaixin168

## 2. 项目结构

```
pyrite-sdk/
├── src/
│   ├── pyrite_sdk/           # 核心 SDK 库
│   │   ├── api/              # API 接口层
│   │   │   ├── ui/           # UI 构建 API（页面、组件、事件、语句）
│   │   │   └── fs/    # 工作区 API（本地/远程文件操作）
│   │   ├── core/             # 核心模块（Bridge、Plugin）
│   │   ├── interfaces/       # 类型接口定义
│   │   ├── models/           # 数据模型（Schema、常量）
│   │   └── utils/            # 工具类（配置、UI 序列化）
│   └── packager/             # CLI 打包工具
├── examples/                 # 示例代码
├── docs/                     # 文档目录
├── build/                    # 构建输出
├── pyproject.toml            # 项目配置
└── uv.lock                   # 依赖锁定文件
```

## 3. 核心架构

### 3.1 WebSocket 通信层（Bridge）

SDK 通过 WebSocket 与 PyriteIDE 进行双向通信，采用 JSON 序列化的消息信封格式。

- **SDK 角色**: WebSocket Server
- **IDE 角色**: WebSocket Client
- **端口**: 通过环境变量 `PYRITE_IDE_PLUGIN_PORT` 指定
- **协议规范**: 详见 `docs/websockets.md`

**核心消息类型**:

| 方向 | 类型 | 说明 |
|------|------|------|
| SDK → IDE | `sdk.page.push` | 推送页面 UI 描述 |
| SDK → IDE | `sdk.var.set` | 设置响应式变量 |
| SDK → IDE | `sdk.path.request` | 请求资源路径 |
| SDK → IDE | `sdk.file.*` | 本地工作区操作（文件列表、创建、删除等） |
| IDE → SDK | `ide.event.callback` | 用户交互事件回调 |
| IDE → SDK | `ide.lifecycle.hook` | 生命周期钩子 |
| IDE → SDK | `ide.page.refresh` | 触发 UI 刷新 |

### 3.2 插件基类（Plugin）

所有插件必须继承 `Plugin` 抽象基类，实现必要的生命周期方法：

```python
from pyrite_sdk.core.plugin import Plugin

class MyPlugin(Plugin):
    def on_start(self):
        """插件启动时调用（必须实现）"""
        pass

    def on_dispose(self):
        """插件销毁时调用（必须实现）"""
        pass

    def on_pause(self):
        """插件暂停时调用（可选）"""
        pass

    def on_resume(self):
        """插件恢复时调用（可选）"""
        pass

    def on_refresh(self):
        """UI 刷新时调用（可选）"""
        pass
```

**Plugin 核心属性**:
- `pages: dict[str, Page]` - 注册的页面集合
- `bridge: Bridge` - WebSocket 通信桥接器
- `file: File` - 本地工作区操作接口
- `board: Board` - 远程工作区操作接口（占位实现）
- `cfg: Cfg` - 插件配置（从 `plugin.toml` 加载）
- `assets: Path` - 插件资产路径

### 3.3 UI 构建系统

SDK 提供了一套声明式的 UI 构建 API，使用 Python 上下文管理器语法构建组件树，最终生成 RFW（Remote Flutter Widgets）格式代码。

#### 组件（Widgets）

| 组件 | 说明 |
|------|------|
| `Container` | 容器组件，支持边距、装饰等 |
| `Column` | 垂直布局 |
| `Row` | 水平布局 |
| `Center` | 居中布局 |
| `Expanded` | 弹性填充 |
| `FittedBox` | 自适应缩放 |
| `Padding` / `SizedBox` / `Align` | 常用布局辅助 |
| `Stack` / `Positioned` / `Wrap` | 多子组件布局 |
| `SingleChildScrollView` / `ListView` | 滚动列表 |
| `SafeArea` / `Divider` / `Card` | 常用 Material/布局组件 |
| `Text` | 文本组件 |
| `TextField` | 文本输入组件 |
| `Checkbox` / `Switch` / `RadioGroup` / `Slider` / `DropdownButton` | 选择与滑动输入 |
| `TextButton` / `ElevatedButton` / `OutlinedButton` / `FilledButton` / `IconButton` / `FloatingActionButton` | 按钮组件 |
| `Icon` / `Image` / `VideoPlayer` | 图标、本地/网络/打包资源图片和视频播放 |
| `ListTile` / `Tooltip` / `Chip` / `ExpansionTile` | 列表项、提示、标签和可展开内容 |
| `CircularProgressIndicator` / `LinearProgressIndicator` | 进度指示器 |
| `GestureDetector` | 手势检测器 |
| `Scaffold` / `AppBar` | 页面脚手架 |
| `NewWidget` | 自定义组件定义 |
| `Widget` | 引用已有组件 |
| `VarWidget` | 变量绑定组件 |

#### 语句（Sentences）

| 语句 | 说明 |
|------|------|
| `Var` | 变量引用（`data.xxx`, `args.xxx`, `state.xxx`） |
| `Expr` / `Ref` / `expr` / `ref` / `call` / `ternary` | RFW 表达式、命名空间引用、调用和三元条件 |
| `let` | 变量赋值语句 |
| `Match` / `Case` / `DefaultCase` | 模式匹配（条件渲染） |
| `ForLoop` | 循环语句，支持构造参数或 `with` 嵌套子组件 |

#### 事件系统

```python
from pyrite_sdk.api.ui.event import Event

# 定义事件回调
def on_button_click(**kwargs):
    print("Button clicked", kwargs)

# 绑定到组件
button = TextButton(on_pressed=Event(on_button_click, args={"id": 0}))
```

### 3.4 工作区 API

#### File（本地工作区）

| 方法 | 说明 |
|------|------|
| `get_root_dir(callback)` | 获取根目录 |
| `get_file_list(path, callback)` | 获取文件列表 |
| `get_focus_file_node(callback)` | 获取当前聚焦的文件 |
| `get_focus_folder_node(callback)` | 获取当前聚焦的文件夹 |
| `create_file(name, parent_path, callback)` | 创建文件 |
| `create_folder(name, parent_path, callback)` | 创建文件夹 |
| `open_file(path)` | 打开文件 |
| `open_folder(path)` | 打开文件夹 |
| `rename_file(path, new_name)` | 重命名文件 |
| `delete_file(path)` | 删除文件 |
| `save_current_file()` | 保存当前文件 |
| `save_current_file_as()` | 另存为 |
| `upload_selected_local_file_item()` | 上传选中的本地文件 |

#### Dialog（系统对话框）

| 方法 | 说明 |
|------|------|
| `open_folder(title=None, initial_directory=None, callback=None)` | 打开系统文件夹选择器，回调的 `data` 为选中的目录路径，取消时为 `None` |

## 4. 快速开始

### 4.1 安装依赖

```bash
uv sync
# 或
pip install -e .
```

### 4.2 编写插件

```python
from pyrite_sdk.api.ui.widgets import *
from pyrite_sdk.api.ui.page import Page
from pyrite_sdk.api.ui.event import Event
from pyrite_sdk.api.ui.sentence import *
from pyrite_sdk.models.consts import Package
from pyrite_sdk.core.plugin import Plugin

# 构建页面
page = Page(packages=[Package.core.widgets, Package.core.material])

root = NewWidget("root").add_to(page)
with Container().add_to(root):
    with Column():
        Text("Hello, PyriteSDK!")
        with TextButton(on_pressed=Event(lambda **kw: print("clicked"))):
            Text("Click Me")

# 定义插件
class MyPlugin(Plugin):
    def __init__(self):
        super().__init__()
        self.pages = {"home": page}

    def on_start(self):
        print("Plugin started")

    def on_dispose(self):
        print("Plugin disposed")

# 启动插件
if __name__ == "__main__":
    plugin = MyPlugin()
    plugin.start()
```

### 4.3 插件配置（plugin.toml）

```toml
[general]
name = "My Plugin"
id = "my-plugin"
version = "1.0.0"
author = "Your Name"

[permissions]
ui = true

[platform]
linux = true
macos = true
windows = true
```

## 5. 打包工具（Packager）

SDK 包含一个 CLI 打包工具，用于为 serious_python 处理 Python 应用和依赖。

### 5.1 使用方式

```bash
# 交互模式
pyrsdk package -i

# 命令行模式
pyrsdk package . -p Android --python-version 3.14 \
  --arch arm64-v8a -r requests -a build/app.zip
```

### 5.2 支持的平台

| 平台 | 架构 |
|------|------|
| Android | arm64-v8a, armeabi-v7a, x86_64 |
| macOS (Darwin) | arm64, x86_64 |
| Windows | (默认) |
| Linux | (默认) |

### 5.3 打包流程

1. 复制应用代码到临时目录
2. （可选）编译 Python 源文件为 .pyc
3. （可选）清理不必要的文件
4. （可选）安装 Python 依赖包（支持 `uv` 或 `pip`）
5. 设置 `SERIOUS_PYTHON_APP` 时暂存原生应用目录；否则创建插件 ZIP
6. ZIP 输出生成 SHA256 哈希文件

### 5.4 主要参数

| 参数 | 说明 |
|------|------|
| `source_dir` | 源代码目录 |
| `-p, --platform` | 目标平台 |
| `--python-version` | 目标 Python 版本（3.12/3.13/3.14） |
| `--arch` | 目标架构 |
| `-r, --requirements` | 依赖包列表 |
| `-a, --asset` | 输出路径（默认 `build/app.zip`） |
| `--compile-app` | 编译 Python 源码 |
| `--cleanup` | 清理冗余文件 |
| `--pip-tool` | 依赖安装工具（uv/pip） |

`SERIOUS_PYTHON_VERSION` 可设置默认目标版本；`--python-version` 优先。
依赖目录可通过 `SERIOUS_PYTHON_SITE_PACKAGES` 指定。设置
`SERIOUS_PYTHON_APP` 后，未显式传入 `--asset` 的原生打包会把处理后的
应用暂存到该目录。显式传入 `--asset` 时仍生成 ZIP 和哈希文件。

## 6. 依赖项

| 包 | 版本 | 用途 |
|----|------|------|
| pydantic | 1.8.2 | 数据模型验证 |
| websockets | >= 16.0 | WebSocket 通信 |
| typer | >= 0.25.1 | CLI 框架 |
| rich | >= 13.0.0 | 终端美化输出 |
| build | >= 1.4.3 | 构建工具 |
| setuptools | >= 82.0.1 | 打包工具 |

## 7. 开发指南

### 7.1 构建项目

```bash
python -m build
```

### 7.2 运行示例

```bash
cd examples
python -m examples
```

### 7.3 代码规范

- 使用 Python 类型注解
- 遵循 Pydantic v1 模型定义
- UI 组件使用上下文管理器语法（`with` 语句）
- 事件回调使用关键字参数传递

## 8. 许可证

本项目采用 [GNU Affero General Public License v3.0](LICENSE) 许可证。
