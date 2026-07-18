# IDE 命令与权限

本页记录 PyriteSDK 当前会发送的 IDE 命令，以及 PyriteIDE 主机端 `Permissions.commandRequirements` 对应的权限。权限在插件的 `plugin.toml` 中声明。

```toml
[permissions]
ui = ["view", "navigate"]
file = ["read", "write"]
editor = ["read"]
```

权限值也可写为 `true`，表示声明该资源的全部已知动作。`write` 隐含同资源的 `read`，适用于 `file`、`board`、`editor`、`persistence`、`serial` 和 `data`。

## UI

| 命令 | 权限 |
| --- | --- |
| `sdk.page.push` | `ui:view` |
| `sdk.var.set` | `ui:view` |
| `sdk.callback.register` | `ui:view` |
| `sdk.callback.clear` | `ui:view` |
| `sdk.callback.set` | `ui:view` |
| `sdk.router.push` | `ui:navigate` |
| `sdk.router.pop` | `ui:navigate` |
| `sdk.router.replace` | `ui:navigate` |
| `sdk.router.goto` | `ui:navigate` |

`sdk.callback.*` 由 Bridge 在刷新和变量绑定过程中自动发送，UI 插件应声明 `ui:view`。

## 本地工作区

| 命令 | 权限 |
| --- | --- |
| `sdk.file.get_dir_list` | `file:read` |
| `sdk.file.get_root_dir` | `file:read` |
| `sdk.file.read_file` | `file:read` |
| `sdk.file.exists` | `file:read` |
| `sdk.file.is_file` | `file:read` |
| `sdk.file.is_directory` | `file:read` |
| `sdk.file.get_focus_file_node` | `file:read` |
| `sdk.file.get_focus_folder_node` | `file:read` |
| `sdk.file.get_unique_name` | `file:read` |
| `sdk.file.open_file` | `file:read` |
| `sdk.file.open_folder` | `file:read` |
| `sdk.file.upload_file` | `file:read` |
| `sdk.file.upload_selected_local_file_item` | `file:read` |
| `sdk.file.write_file` | `file:write` |
| `sdk.file.create_file` | `file:write` |
| `sdk.file.create_folder` | `file:write` |
| `sdk.file.delete` | `file:write` |
| `sdk.file.rename` | `file:write` |
| `sdk.file.copy_file` | `file:write` |
| `sdk.file.move_file` | `file:write` |
| `sdk.file.save_current_file` | `file:write` |
| `sdk.file.save_current_file_as` | `file:write` |

## Board

| 命令 | 权限 |
| --- | --- |
| `sdk.board.get_dir_list` | `board:read` |
| `sdk.board.get_root_dir` | `board:read` |
| `sdk.board.read_file` | `board:read` |
| `sdk.board.exists` | `board:read` |
| `sdk.board.is_file` | `board:read` |
| `sdk.board.is_directory` | `board:read` |
| `sdk.board.get_focus_file_node` | `board:read` |
| `sdk.board.get_focus_folder_node` | `board:read` |
| `sdk.board.get_corresponding_file_path` | `board:read` |
| `sdk.board.download_file` | `board:read` |
| `sdk.board.download_selected_board_item` | `board:read` |
| `sdk.board.write_file` | `board:write` |
| `sdk.board.delete_file` | `board:write` |
| `sdk.board.delete_folder` | `board:write` |
| `sdk.board.rename` | `board:write` |

## 编辑器

| 权限 | 命令 |
| --- | --- |
| `editor:read` | `sdk.editor.get_text`, `sdk.editor.get_line_count`, `sdk.editor.get_line_text`, `sdk.editor.get_selected_text`, `sdk.editor.get_cursor_position`, `sdk.editor.get_selection`, `sdk.editor.can_undo`, `sdk.editor.can_redo`, `sdk.editor.get_current_tab`, `sdk.editor.list_tabs`, `sdk.editor.find`, `sdk.editor.find_regex`, `sdk.editor.clear_search`, `sdk.editor.copy` |
| `editor:write` | `sdk.editor.set_text`, `sdk.editor.insert_text`, `sdk.editor.replace_range`, `sdk.editor.clear`, `sdk.editor.set_cursor_position`, `sdk.editor.set_selection`, `sdk.editor.select_all`, `sdk.editor.go_to_line`, `sdk.editor.undo`, `sdk.editor.redo`, `sdk.editor.open_file`, `sdk.editor.close_tab`, `sdk.editor.set_ghost_text`, `sdk.editor.clear_ghost_text`, `sdk.editor.scroll_to_line`, `sdk.editor.cut`, `sdk.editor.paste` |

## 持久化与设置

| 命令 | 权限 |
| --- | --- |
| `sdk.persistence.get` | `persistence:read` |
| `sdk.persistence.list_groups` | `persistence:read` |
| `sdk.persistence.list_keys` | `persistence:read` |
| `sdk.persistence.set` | `persistence:write` |
| `sdk.persistence.delete` | `persistence:write` |
| `sdk.persistence.clear` | `persistence:write` |
| `sdk.settings.get` | `settings:read` |
| `sdk.settings.list` | `settings:read` |
| `sdk.settings.set` | `settings:write` |

## 串口

| 权限 | 命令 |
| --- | --- |
| `serial:read` | `sdk.serial.list_ports`, `sdk.serial.get_status`, `sdk.serial.read` |
| `serial:write` | `sdk.serial.connect`, `sdk.serial.disconnect`, `sdk.serial.send`, `sdk.serial.send_command`, `sdk.serial.run_python`, `sdk.serial.set_baud_rate`, `sdk.serial.set_auto_reconnect` |

## 数据贡献

| 权限 | 命令 |
| --- | --- |
| `data:read` | `sdk.theme.get`, `sdk.theme.list`, `sdk.i18n.get`, `sdk.i18n.list` |
| `data:write` | `sdk.theme.contribute`, `sdk.theme.register_runtime`, `sdk.theme.revoke`; `sdk.i18n.contribute`, `sdk.i18n.register_runtime`, `sdk.i18n.revoke`; `sdk.stubs.contribute`, `sdk.stubs.register_runtime`, `sdk.stubs.revoke` |

## 对话框

| 命令 | 权限 |
| --- | --- |
| `sdk.dialog.open_folder` | `dialog:show` |

## 主机端保留命令

PyriteIDE 当前还为以下 Tab 命令定义权限，但本仓库没有对应的 Python SDK 封装：

| 命令 | 权限 |
| --- | --- |
| `sdk.tab.create_file` | `tab:create` |
| `sdk.tab.create_custom` | `tab:create` |
| `sdk.tab.close` | `tab:manage` |
| `sdk.tab.list` | `tab:manage` |
| `sdk.tab.switch` | `tab:manage` |

## 当前未映射权限的命令

以下命令存在于 SDK 或 IDE API，但当前不在主机端权限映射中，因此无需在 `plugin.toml` 中声明对应权限：

- 基础设施：`sdk.path.request`、`sdk.output.append`、`sdk.message.show`
- Board：`sdk.board.open_file`
- Stubs 查询：`sdk.stubs.get`、`sdk.stubs.list`、`sdk.stubs.resolve_layers`

这一节描述的是当前实现，不表示这些命令永远不需要权限。新增或调整命令时，应同步更新 SDK 封装、IDE 命令处理器、IDE 权限映射和本文档。
