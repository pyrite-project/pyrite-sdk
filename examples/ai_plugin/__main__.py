from pathlib import Path
import json
import re
import ssl
import tempfile
import threading
import time
from typing import Any, Callable, Iterable
import urllib.error
import urllib.request

from pyrite_sdk.api.ui import *
from pyrite_sdk.core.plugin import UiPlugin
from pyrite_sdk.models.consts import Package, PathScope, Ui


CONFIG_GROUP = "ai_chat"
DEFAULT_API_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-v4-pro"
DEFAULT_VERIFY_TLS = False
DEFAULT_AUTO_PROCESS_URL = True
DEFAULT_MARKDOWN_CODE_FONT_FAMILY = ""
DEFAULT_MARKDOWN_DARK_CODE_BLOCKS = False
DEFAULT_USE_VIBE_SKILL = True
DEFAULT_THINKING_ENABLED = True
DEFAULT_REASONING_EFFORT = "max"
REFRESH_INTERVAL = 0.08
MAX_DIFF_REPAIR_ROUNDS = 3
VIBE_SKILL_RELATIVE_PATH = Path("skills") / "vibe-coding" / "SKILL.md"
DIFF_BLOCK_RE = re.compile(
    r"(?ms)^\[DIFF:([^\]\n]+)\]\s*\n```(?:diff|patch)?\s*\n(.*?)\n```"
)
WORKSPACE_REF_RE = re.compile(r"@(file|board):([^\s`]+)")
READ_REQUEST_RE = re.compile(r"(?im)^\s*\[READ:(file|board):([^\]\n]+)\]\s*$")
HUNK_HEADER_RE = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
    r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@(?: .*)?$"
)


class MarkdownRenderOptions:
    # Keep markdown display settings together so nested render helpers stay small.
    def __init__(
        self,
        code_font_family: str = "",
        dark_code_blocks: bool = DEFAULT_MARKDOWN_DARK_CODE_BLOCKS,
    ) -> None:
        self.code_font_family = (code_font_family or "").strip()
        self.dark_code_blocks = bool(dark_code_blocks)


SYSTEM_PROMPT = """你是 PyriteIDE 中的 AI 对话助手，是用户的结对编程代理。

工作方式：
- 先理解目标和上下文，再输出修改。
- 如果要修改未在当前请求上下文中读取过的文件，必须先请求读取文件，不要猜测文件内容。
- 输出 DIFF 前必须确认目标文件内容来自当前 `<workspace_context>`。
- 任务明确时主动推进，不要用“你可以继续让我...”这类空泛收尾。
- 多文件、行为变更或有风险时，先给很短的计划；简单修改直接给结果。
- 最终回答应说明已做什么、建议如何验证，或明确剩余风险。

如果需要读取项目文件才能继续，输出一行或多行读取请求，插件会读取后自动继续请求：

[READ:file:path/to/file.py]
[READ:board:/path/to/file.py]

当你建议修改用户项目中的代码文件内容，并且希望用户可以一键应用时，必须使用下面的 patch-ng 兼容 unified diff 格式：

[DIFF:path/to/file.py]
```diff
--- path/to/file.py
+++ path/to/file.py
@@ -1,2 +1,2 @@
-旧内容
+新内容
```

新增空文件或空文件新增内容时使用：

[DIFF:path/to/file.py]
```diff
--- /dev/null
+++ path/to/file.py
@@ -0,0 +1,2 @@
+第一行
+第二行
```

要求：
- 需要文件内容时不要编造，先输出 [READ:...]。
- [READ:...] 用于读取文件，不要和最终回答混在一起；读取后插件会自动继续。
- 未读取当前目标文件时，不要输出 [DIFF:...]，先输出 [READ:file:path]。
- 每个文件单独使用一个 [DIFF:...] 块。
- [DIFF:...] 中填写要修改的项目文件路径，优先使用相对项目根目录的路径。
- diff 代码块必须是标准 unified diff，包含 `---`、`+++` 和 `@@` hunk。
- hunk 内每一行必须以空格、`-` 或 `+` 开头；不要省略 hunk 内必要的上下文行。
- 输出前先模拟应用 DIFF：确认 hunk 行数、缩进、上下文、import 和 API 都与当前文件一致。
- 优先输出小而稳定的 hunk；如果修改范围很大，拆成多个 hunk，不要靠猜测行数。
- 不要把解释文字放进 diff 代码块内部。
- 如果只是解释代码、给出示例代码、展示片段，或者回答中没有要应用到用户项目文件的修改，不要使用 [DIFF:...]，直接使用普通 Markdown 代码块。

插件会在写入文件前把 DIFF 临时应用到当前文件副本中。如果你收到 `<diff_validation_failed>`：
- 这表示你的 DIFF 没有通过 patch-ng 预检，必须基于错误信息和当前文件重新生成。
- 只输出修正后的 `[DIFF:...]` 块；不要重复无效 DIFF，不要解释失败原因。
- 优先修复常见错误：`---`、`+++`、`@@` 被压在同一行；hunk header 行数和实际行数不一致；hunk 内空白行没有前缀；上下文来自旧文件；删除了新代码仍需要的 import；使用了未确认存在的 API。
- 重新计算每个 hunk 的 `@@ -old_start,old_count +new_start,new_count @@`：空格行同时计入 old/new，`-` 只计入 old，`+` 只计入 new。
"""


def _input_decoration(label: str, hint: str = "", helper: str = ""):
    return call(
        "InputDecoration",
        label_text=label,
        hint_text=hint,
        helper_text=helper or None,
        is_dense=True,
    )


def _section_title(text: str) -> None:
    Text(
        text,
        style=TextStyle(font_size=13, font_weight=FontWeight.bold),
    )


def _endpoint_url(api_url: str, auto_process_url: bool = DEFAULT_AUTO_PROCESS_URL) -> str:
    url = (api_url or DEFAULT_API_URL).strip().rstrip("/")
    if not auto_process_url:
        return url
    if url.endswith("/chat/completions") or url.endswith("/responses"):
        return url
    return f"{url}/chat/completions"


def _is_missing_value(value: Any) -> bool:
    if value is None:
        return True
    type_name = type(value).__name__.strip().lower()
    if type_name == "missing":
        return True
    if isinstance(value, str):
        text = value.strip().lower()
        return text in {"missing", "<missing>", "missing()"}
    return False


def _coerce_text(value: Any, default: str = "", allow_empty: bool = False) -> str:
    if _is_missing_value(value):
        return default
    text = value.strip() if isinstance(value, str) else str(value).strip()
    if text:
        return text
    return "" if allow_empty else default


def _coerce_bool(value: Any, default: bool = True) -> bool:
    if _is_missing_value(value):
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off"}:
            return False
    if value is None:
        return default
    return bool(value)


def _normalize_reasoning_effort(
    value: Any,
    default: str = DEFAULT_REASONING_EFFORT,
) -> str:
    return _coerce_text(value, default)


def _clean_workspace_ref_path(path: str) -> str:
    return path.strip().strip("<>()[]{}").rstrip(".,;，。")


def _extract_workspace_refs(prompt: str) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for match in WORKSPACE_REF_RE.finditer(prompt or ""):
        source = match.group(1)
        path = _clean_workspace_ref_path(match.group(2))
        if not path:
            continue
        key = (source, path)
        if key in seen:
            continue
        seen.add(key)
        refs.append({"source": source, "path": path})
    return refs


def _extract_ai_read_refs(content: str) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for match in READ_REQUEST_RE.finditer(content or ""):
        source = match.group(1)
        path = _clean_workspace_ref_path(match.group(2))
        if not path:
            continue
        key = (source, path)
        if key in seen:
            continue
        seen.add(key)
        refs.append({"source": source, "path": path})
    return refs


def _extract_diff_blocks(content: str) -> list[dict[str, str]]:
    blocks: list[dict[str, str]] = []
    for match in DIFF_BLOCK_RE.finditer(content or ""):
        path = match.group(1).strip()
        diff = match.group(2)
        if path and diff.strip():
            blocks.append({"path": path, "diff": diff})
    return blocks


def _ai_read_request_notice(refs: list[dict[str, str]]) -> str:
    paths = [f"`{ref['path']}`" for ref in refs]
    return "AI 请求读取：" + "、".join(paths)


def _assistant_message() -> dict[str, Any]:
    return {
        "role": "assistant",
        "content": "",
        "reasoning_content": "",
        "show_reasoning": False,
        "diff_validation_notice": "",
    }


def _diff_declares_new_file(diff_text: str) -> bool:
    body = _patch_body(diff_text)
    return (
        re.search(r"(?m)^--- /dev/null$", diff_text.strip()) is not None
        or re.search(r"(?m)^@@ -0,0 \+\d+(?:,\d+)? @@", body) is not None
    )


def _format_workspace_context(results: list[dict[str, Any]]) -> str:
    if not results:
        return ""
    blocks: list[str] = []
    for result in results:
        source = result["source"]
        path = result["path"]
        content = result.get("content")
        error = result.get("error")
        if isinstance(content, str):
            blocks.append(
                f'<workspace_file source="{source}" path="{path}">\n'
                f"{content}\n"
                f"</workspace_file>"
            )
        else:
            error_message = error or "读取失败"
            blocks.append(
                f'<workspace_file source="{source}" path="{path}" error="{error_message}" />'
            )
    return "<workspace_context>\n" + "\n\n".join(blocks) + "\n</workspace_context>"


def _workspace_read_notice(results: list[dict[str, Any]]) -> str:
    loaded = [
        f"`{result['path']}`"
        for result in results
        if isinstance(result.get("content"), str)
    ]
    failed = [
        f"`{result['path']}`"
        for result in results
        if not isinstance(result.get("content"), str)
    ]
    parts: list[str] = []
    if loaded:
        parts.append("AI 已读取：" + "、".join(loaded))
    if failed:
        parts.append("读取失败：" + "、".join(failed))
    return "\n".join(parts)


def _diff_validation_success_notice(blocks: list[dict[str, str]]) -> str:
    paths = [f"`{block['path']}`" for block in blocks]
    return "Diff 已通过临时应用检查：" + "、".join(paths)


def _diff_validation_failure_notice(
    failures: list[dict[str, Any]],
    retry_round: int,
) -> str:
    paths = [f"`{failure['path']}`" for failure in failures]
    detail = "\n".join(
        f"- `{failure['path']}`：{failure['error']}" for failure in failures
    )
    if retry_round >= MAX_DIFF_REPAIR_ROUNDS:
        return (
            "Diff 预检仍未通过，已达到自动重试上限："
            + "、".join(paths)
            + ("\n" + detail if detail else "")
        )
    return (
        "Diff 预检失败，AI 正在根据错误重试："
        + "、".join(paths)
        + ("\n" + detail if detail else "")
    )


def _format_diff_repair_prompt(
    failures: list[dict[str, Any]],
    retry_round: int,
) -> str:
    blocks: list[str] = []
    for index, failure in enumerate(failures, start=1):
        content = failure.get("original_text")
        current_file = ""
        if isinstance(content, str):
            current_file = (
                f'<current_file path="{failure["path"]}">\n'
                f"{content}\n"
                f"</current_file>"
            )
        else:
            current_file = (
                f'<current_file path="{failure["path"]}" '
                f'error="{failure.get("read_error") or "无法读取当前文件"}" />'
            )
        blocks.append(
            f"<diff_failure index=\"{index}\">\n"
            f"<path>{failure['path']}</path>\n"
            f"<error>{failure['error']}</error>\n"
            f"{current_file}\n"
            f"<failed_diff>\n{failure['diff']}\n</failed_diff>\n"
            f"</diff_failure>"
        )

    return (
        "<diff_validation_failed>\n"
        f"<attempt>{retry_round}</attempt>\n"
        + "\n\n".join(blocks)
        + "\n</diff_validation_failed>\n\n"
        "你的上一个 DIFF 没有通过插件的临时 patch-ng 校验。请基于上面的当前文件和错误重新输出修正后的 DIFF。\n"
        "必须遵守：\n"
        "1. 只输出需要修正的 `[DIFF:...]` 块，不要解释，不要输出普通代码块。\n"
        "2. `---`、`+++`、`@@` 必须各占一行。\n"
        "3. hunk 内每一行必须以空格、`-` 或 `+` 开头；空白行也必须有前缀。\n"
        "4. 重新计算 hunk header 行数：空格行同时计入 old/new，`-` 只计入 old，`+` 只计入 new。\n"
        "5. 必须基于 `<current_file>`，不要使用旧上下文；保留新代码仍需要的 import 和已经确认存在的 API。\n"
    )


def _markdown_code_palette(options: MarkdownRenderOptions) -> dict[str, int]:
    if options.dark_code_blocks:
        return {
            "block_background": 0xFF111827,
            "block_border": 0xFF374151,
            "fallback_text": 0xFFE5E7EB,
            "inline_background": 0xFF374151,
            "inline_text": 0xFFF9FAFB,
        }
    return {
        "block_background": 0xFFF8FAFC,
        "block_border": 0xFFE2E8F0,
        "fallback_text": 0xFF1F2937,
        "inline_background": 0xFFEFF4FA,
        "inline_text": 0xFF0F172A,
    }


def _markdown_code_font_style(options: MarkdownRenderOptions) -> Any:
    style_args: dict[str, Any] = {
        "font_size": 13,
        "height": 1.45,
    }
    if options.code_font_family:
        style_args["font_family"] = options.code_font_family
    return TextStyle(**style_args)


def _markdown_inline_code_style(options: MarkdownRenderOptions) -> Any:
    palette = _markdown_code_palette(options)
    style_args: dict[str, Any] = {
        "color": color(palette["inline_text"]),
        "background_color": color(palette["inline_background"]),
        "font_size": 13,
        "height": 1.25,
    }
    if options.code_font_family:
        style_args["font_family"] = options.code_font_family
    return TextStyle(**style_args)


def _markdown_block(content: str, options: MarkdownRenderOptions) -> None:
    palette = _markdown_code_palette(options)
    code_font_style = _markdown_code_font_style(options)
    code_decoration = BoxDecoration(
        color=color(palette["block_background"]),
        border=Border.all(color=color(palette["block_border"])),
        border_radius=BorderRadius.circular(6),
    )
    MarkdownBlock(
        content,
        selectable=True,
        code_block_padding=EdgeInsets.only(left=12, top=10, right=12, bottom=10),
        code_block_margin=EdgeInsets.symmetric(vertical=7),
        code_block_decoration=code_decoration,
        code_block_text_style=code_font_style,
        code_block_style_not_matched=TextStyle(color=color(palette["fallback_text"])),
        code_block_theme="dark" if options.dark_code_blocks else "light",
        inline_code_text_style=_markdown_inline_code_style(options),
    )


def _render_diff_block(
    file_path: str,
    diff_text: str,
    options: MarkdownRenderOptions,
) -> None:
    with Padding(EdgeInsets.only(top=8)):
        with Container(padding=EdgeInsets.all(12)):
            with Column(cross_axis_alignment=CrossAxisAlignment.stretch):
                with Row(cross_axis_alignment=CrossAxisAlignment.center):
                    with Expanded():
                        Text(
                            ["Diff: ", file_path],
                            style=TextStyle(font_size=13, font_weight=FontWeight.bold),
                            soft_wrap=True,
                        )
                    with ElevatedButton(
                        on_pressed=Event(
                            lambda path="", diff="", **_: plugin.apply_diff(path, diff),
                            args={"path": file_path, "diff": diff_text},
                        )
                    ):
                        Text("应用到文件")
                with Padding(EdgeInsets.only(top=8)):
                    _markdown_block(f"```diff\n{diff_text}\n```", options)


def _render_assistant_content(
    content: str,
    options: MarkdownRenderOptions,
) -> None:
    with Column(cross_axis_alignment=CrossAxisAlignment.stretch):
        position = 0
        found = False
        for match in DIFF_BLOCK_RE.finditer(content):
            before = content[position:match.start()]
            if before.strip():
                with Padding(EdgeInsets.only(top=8 if not found else 12)):
                    _markdown_block(before, options)
            _render_diff_block(match.group(1).strip(), match.group(2), options)
            found = True
            position = match.end()

        rest = content[position:]
        if rest.strip():
            with Padding(EdgeInsets.only(top=8 if not found else 12)):
                _markdown_block(rest, options)
            found = True

        if not found:
            with Padding(EdgeInsets.only(top=8)):
                _markdown_block(content, options)


def _safe_patch_target(path: str) -> Path:
    parts = [
        part
        for part in path.replace("\\", "/").split("/")
        if part and part not in {".", ".."} and not part.endswith(":")
    ]
    if not parts:
        return Path("target.txt")
    return Path(*parts)


def _patch_body(diff_text: str) -> str:
    lines = diff_text.strip("\n").splitlines()
    for index, line in enumerate(lines[:-1]):
        if line.startswith("--- ") and lines[index + 1].startswith("+++ "):
            return "\n".join(lines[index + 2 :])
    return "\n".join(lines)


def _hunk_count(value: str | None) -> int:
    return int(value) if value is not None else 1


def _line_marker_error(line_number: int, line: str) -> str:
    if line == "":
        return f"第 {line_number} 行是裸空行；hunk 内空白行也必须写成带前缀的一行，例如只包含一个空格。"
    return (
        f"第 {line_number} 行缺少 diff 前缀：{line!r}。"
        "hunk 内每一行都必须以空格、`-` 或 `+` 开头。"
    )


def _validate_unified_diff_structure(patch_text: str) -> None:
    lines = patch_text.strip("\n").splitlines()
    if len(lines) < 3:
        raise ValueError("diff 太短，必须包含 `---`、`+++` 和至少一个 `@@` hunk")
    for line_number, line in enumerate(lines, start=1):
        if line.startswith("--- ") and "+++ " in line:
            raise ValueError(
                f"第 {line_number} 行把 `---` 和 `+++` 写在同一行，请分成两行。"
            )
        if line.startswith("+++ ") and "@@ " in line:
            raise ValueError(
                f"第 {line_number} 行把 `+++` 和 `@@` 写在同一行，请分成两行。"
            )
    if not lines[0].startswith("--- "):
        raise ValueError("diff 第一行必须是 `--- old/path` 或 `--- /dev/null`")
    if not lines[1].startswith("+++ "):
        raise ValueError("diff 第二行必须是 `+++ new/path`")

    index = 2
    hunk_seen = False
    while index < len(lines):
        header_number = index + 1
        header = lines[index]
        match = HUNK_HEADER_RE.match(header)
        if not match:
            raise ValueError(
                f"第 {header_number} 行不是合法 hunk header：{header!r}。"
                "格式必须类似 `@@ -1,3 +1,4 @@`。"
            )
        hunk_seen = True
        expected_old = _hunk_count(match.group("old_count"))
        expected_new = _hunk_count(match.group("new_count"))
        actual_old = 0
        actual_new = 0
        index += 1

        while index < len(lines) and not lines[index].startswith("@@ "):
            line_number = index + 1
            line = lines[index]
            if line.startswith("\\ No newline at end of file"):
                index += 1
                continue
            marker = line[:1]
            if marker not in {" ", "-", "+"}:
                raise ValueError(_line_marker_error(line_number, line))
            if marker in {" ", "-"}:
                actual_old += 1
            if marker in {" ", "+"}:
                actual_new += 1
            index += 1

        if actual_old != expected_old or actual_new != expected_new:
            raise ValueError(
                f"第 {header_number} 行 hunk header 行数不匹配：声明旧文件 "
                f"{expected_old} 行、新文件 {expected_new} 行；实际旧文件 "
                f"{actual_old} 行、新文件 {actual_new} 行。"
            )

    if not hunk_seen:
        raise ValueError("diff 缺少 `@@` hunk header")


def _patch_ng_text(original_text: str, diff_text: str, target_path: str) -> str:
    target = _safe_patch_target(target_path).as_posix()
    body = _patch_body(diff_text)
    if not body.strip():
        raise ValueError("diff 内容缺少 hunk")
    old_path = "/dev/null" if original_text == "" and "@@ -0,0 " in body else target
    return f"--- {old_path}\n+++ {target}\n{body}\n"


def _apply_unified_diff(original_text: str, diff_text: str, target_path: str) -> str:
    try:
        import patch_ng
    except ImportError as exc:
        raise RuntimeError("缺少 patch-ng 依赖，请安装插件 requirements.txt") from exc

    target = _safe_patch_target(target_path)
    patch_text = _patch_ng_text(original_text, diff_text, target.as_posix())
    _validate_unified_diff_structure(patch_text)
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        target_file = root / target
        target_file.parent.mkdir(parents=True, exist_ok=True)
        if not patch_text.startswith("--- /dev/null\n"):
            target_file.write_text(original_text, encoding="utf-8")

        patch_set = patch_ng.fromstring(patch_text.encode("utf-8"))
        if not patch_set:
            raise ValueError("patch-ng 无法解析 unified diff")
        if not patch_set.apply(root=str(root), fuzz=False):
            raise ValueError("patch-ng 无法应用 diff，请检查 hunk 上下文是否与当前文件一致")
        return target_file.read_text(encoding="utf-8") if target_file.exists() else ""


def _is_absolute_diff_path(path: str) -> bool:
    return Path(path).expanduser().is_absolute() or bool(
        re.match(r"^[A-Za-z]:[\\/]", path)
    )


def _resolve_diff_path(path: str, root_dir: str | None) -> str:
    path = path.strip()
    if _is_absolute_diff_path(path):
        return str(Path(path).expanduser())
    if not root_dir:
        raise ValueError("无法获取项目根目录，不能应用相对路径 diff")

    root_path = Path(root_dir).expanduser().resolve()
    target_path = (root_path / path).resolve()
    try:
        target_path.relative_to(root_path)
    except ValueError as exc:
        raise ValueError("diff 文件路径不能位于项目根目录外") from exc
    return str(target_path)


def _message_card(message: dict[str, Any], markdown_options: MarkdownRenderOptions) -> None:
    role = message.get("role", "assistant")
    reasoning_content = message.get("reasoning_content") or ""
    content = message.get("content") or ""
    diff_validation_notice = message.get("diff_validation_notice") or ""
    is_user = role == "user"
    title = "你" if is_user else "提示" if role == "notice" else "AI"
    source_index = message.get("_index", -1)

    with Card(elevation=1, margin=EdgeInsets.only(bottom=12)):
        with Padding(EdgeInsets.all(14)):
            with Column(cross_axis_alignment=CrossAxisAlignment.start):
                Text(
                    title,
                    style=TextStyle(
                        font_size=12,
                        font_weight=FontWeight.bold,
                    ),
                )
                if is_user:
                    with Padding(EdgeInsets.only(top=6)):
                        Text(
                            content,
                            style=TextStyle(font_size=15, height=1.35),
                            soft_wrap=True,
                        )
                else:
                    has_visible_content = bool(
                        content or reasoning_content or diff_validation_notice
                    )
                    if reasoning_content:
                        with Padding(EdgeInsets.only(top=8)):
                            with Container(
                                padding=EdgeInsets.all(10),
                            ):
                                with Column(
                                    cross_axis_alignment=CrossAxisAlignment.stretch
                                ):
                                    with Row(
                                        cross_axis_alignment=CrossAxisAlignment.center
                                    ):
                                        Text(
                                            "思考",
                                            style=TextStyle(
                                                font_size=12,
                                                font_weight=FontWeight.bold,
                                            ),
                                        )
                                        Spacer()
                                        with TextButton(
                                            on_pressed=Event(
                                                lambda index=-1, **_: plugin.toggle_reasoning(
                                                    index
                                                ),
                                                args={"index": source_index},
                                            )
                                        ):
                                            Text(
                                                "收起"
                                                if message.get("show_reasoning")
                                                else "展开"
                                            )
                                    if message.get("show_reasoning"):
                                        with Padding(EdgeInsets.only(top=6)):
                                            _markdown_block(
                                                reasoning_content,
                                                markdown_options,
                                            )
                    if content:
                        if reasoning_content:
                            with Padding(EdgeInsets.only(top=8)):
                                _render_assistant_content(
                                    content,
                                    markdown_options,
                                )
                        else:
                            _render_assistant_content(
                                content,
                                markdown_options,
                            )
                    if role == "assistant" and diff_validation_notice:
                        with Padding(EdgeInsets.only(top=8)):
                            Text(
                                diff_validation_notice,
                                style=TextStyle(font_size=12),
                                soft_wrap=True,
                            )
                    if not has_visible_content:
                        with Padding(EdgeInsets.only(top=8)):
                            Text(
                                "...",
                                style=TextStyle(font_size=15, height=1.35),
                                soft_wrap=True,
                            )


def _switch_tile(title: str, subtitle: str, value: Any, target: Var) -> None:
    ListTile(
        title=Text(title, style=TextStyle(font_size=14, font_weight=FontWeight.bold)),
        subtitle=Text(subtitle, style=TextStyle(font_size=12), soft_wrap=True),
        trailing=Switch(
            value=value,
            on_changed=Event(
                lambda value=True, **_: plugin.bridge.let(target, value)
            ),
        ),
        content_padding=EdgeInsets.symmetric(horizontal=4, vertical=4),
    )


def _text_button(label: str, on_pressed: Event) -> TextButton:
    button = TextButton(on_pressed=on_pressed, add_to_parent=False)
    button.add(Text(label))
    return button


def build_home_page(
    messages: list[dict[str, Any]],
    is_streaming: bool,
    markdown_code_font_family: str,
    markdown_dark_code_blocks: bool,
):
    page = Page(packages=[Package.core.widgets, Package.core.material])
    root = NewWidget(Ui.root).add_to(page)
    action_label = "等待中" if is_streaming else "发送"
    markdown_options = MarkdownRenderOptions(
        markdown_code_font_family,
        markdown_dark_code_blocks,
    )

    with Scaffold(
        app_bar=AppBar(
            title=Text("AI 对话"),
            actions=[
                _text_button("设置", Event(lambda **_: plugin.router.push("settings")))
            ],
        ),
        background_color=None,
    ).add_to(root):
        with SafeArea():
            with Padding(EdgeInsets.all(12)):
                with Column(cross_axis_alignment=CrossAxisAlignment.stretch):
                    with Expanded():
                        with ListView(padding=EdgeInsets.only(bottom=2)):
                            if not messages:
                                with Container(
                                    padding=EdgeInsets.symmetric(vertical=28, horizontal=14),
                                    alignment=Alignment.top_center,
                                ):
                                    Text(
                                        "输入一个问题开始对话。",
                                        style=TextStyle(font_size=15),
                                        text_align=TextAlign.center,
                                    )
                            for item in messages:
                                _message_card(item, markdown_options)

                    with Card(elevation=1, margin=EdgeInsets.only(top=12)):
                        with Padding(EdgeInsets.all(14)):
                            with Column(cross_axis_alignment=CrossAxisAlignment.stretch):
                                TextField(
                                    value=data.prompt,
                                    initial_value="",
                                    decoration=_input_decoration(
                                        "消息",
                                        "请输入问题，可用 @file:main.py 或 @board:/main.py 附加文件",
                                    ),
                                    keyboard_type="multiline",
                                    text_input_action="newline",
                                    min_lines=1,
                                    enabled=not is_streaming,
                                    on_changed=Event(
                                        lambda value="", **_: plugin.bridge.let(data.prompt, value)
                                    ),
                                )
                                with Padding(EdgeInsets.only(top=14)):
                                    with Row(cross_axis_alignment=CrossAxisAlignment.center):
                                        with TextButton(on_pressed=Event(lambda **_: plugin.clear_chat())):
                                            Text("清空")
                                        Spacer()
                                        with ElevatedButton(
                                            on_pressed=Event(
                                                lambda prompt="", **_: plugin.send_prompt(prompt),
                                                args={"prompt": data.prompt},
                                            )
                                        ):
                                            Text(action_label)
    return page


def build_settings_page(
    api_url: str,
    api_key: str,
    model: str,
    verify_tls: bool,
    auto_process_url: bool,
    thinking_enabled: bool,
    reasoning_effort: str,
    use_vibe_skill: bool,
    markdown_code_font_family: str,
    markdown_dark_code_blocks: bool,
    status: str,
    vibe_skill_status: str,
):
    page = Page(packages=[Package.core.widgets, Package.core.material])
    root = NewWidget(Ui.root).add_to(page)
    resolved_url = _endpoint_url(api_url, auto_process_url)

    with Scaffold(
        app_bar=AppBar(
            title=Text("AI 设置"),
            actions=[
                _text_button("主页", Event(lambda **_: plugin.router.goto("home")))
            ]
        )
    ).add_to(root):
        with SafeArea():
            with SingleChildScrollView(padding=EdgeInsets.all(14)):
                with Column(cross_axis_alignment=CrossAxisAlignment.stretch):
                    with Card(elevation=1, margin=EdgeInsets.only(bottom=12)):
                        with Padding(EdgeInsets.all(14)):
                            with Column(cross_axis_alignment=CrossAxisAlignment.stretch):
                                _section_title("连接设置")
                                with Padding(EdgeInsets.only(top=20)):
                                    TextField(
                                        value=data.settings_url,
                                        initial_value=api_url,
                                        decoration=_input_decoration(
                                            "API 地址 / Base URL",
                                            DEFAULT_API_URL,
                                            "开启自动处理时会补全 /chat/completions，支持任意 OpenAI 兼容服务",
                                        ),
                                        keyboard_type="url",
                                        text_input_action="next",
                                        on_changed=Event(
                                            lambda value="", **_: plugin.bridge.let(
                                                data.settings_url, value
                                            )
                                        ),
                                    )
                                with Padding(EdgeInsets.only(top=10)):
                                    _switch_tile(
                                        "自动处理 URL",
                                        "基础地址会自动补全 /chat/completions；关闭后将严格使用你输入的地址。",
                                        data.settings_auto_process_url,
                                        data.settings_auto_process_url,
                                    )
                                with Padding(EdgeInsets.only(top=8)):
                                    Text(
                                        ["请求地址：", resolved_url],
                                        style=TextStyle(font_size=12),
                                        soft_wrap=True,
                                    )
                                with Padding(EdgeInsets.only(top=22)):
                                    TextField(
                                        value=data.settings_api_key,
                                        initial_value=api_key,
                                        decoration=_input_decoration("API 密钥", "sk-...", ""),
                                        obscure_text=True,
                                        text_input_action="done",
                                        on_changed=Event(
                                            lambda value="", **_: plugin.bridge.let(
                                                data.settings_api_key, value
                                            )
                                        ),
                                    )
                                with Padding(EdgeInsets.only(top=22)):
                                    TextField(
                                        value=data.settings_model,
                                        initial_value=model,
                                        decoration=_input_decoration(
                                            "模型",
                                            DEFAULT_MODEL,
                                            "填写当前接口可用的模型名称",
                                        ),
                                        text_input_action="done",
                                        on_changed=Event(
                                            lambda value="", **_: plugin.bridge.let(
                                                data.settings_model, value
                                            )
                                        ),
                                    )
                                with Padding(EdgeInsets.only(top=10)):
                                    _switch_tile(
                                        "思考模式",
                                        "兼容模型支持时会发送 thinking 与 reasoning_effort；不支持这些字段的接口请关闭。",
                                        data.settings_thinking_enabled,
                                        data.settings_thinking_enabled,
                                    )
                                with Padding(EdgeInsets.only(top=22)):
                                    TextField(
                                        value=data.settings_reasoning_effort,
                                        initial_value=reasoning_effort,
                                        decoration=_input_decoration(
                                            "思考强度",
                                            DEFAULT_REASONING_EFFORT,
                                            "填写模型支持的值，例如 low、medium、high、max",
                                        ),
                                        text_input_action="done",
                                        on_changed=Event(
                                            lambda value="", **_: plugin.bridge.let(
                                                data.settings_reasoning_effort, value
                                            )
                                        ),
                                    )
                                with Padding(EdgeInsets.only(top=22)):
                                    TextField(
                                        value=data.settings_markdown_code_font_family,
                                        initial_value=markdown_code_font_family,
                                        decoration=_input_decoration(
                                            "Markdown 代码字体",
                                            "留空使用 IDE 默认字体",
                                            "例如 Menlo、SF Mono 或 JetBrains Mono",
                                        ),
                                        text_input_action="done",
                                        on_changed=Event(
                                            lambda value="", **_: plugin.bridge.let(
                                                data.settings_markdown_code_font_family, value
                                            )
                                        ),
                                    )
                                with Padding(EdgeInsets.only(top=10)):
                                    _switch_tile(
                                        "Markdown 深色代码块",
                                        "开启后 Markdown 的代码段和代码块使用深色样式。",
                                        data.settings_markdown_dark_code_blocks,
                                        data.settings_markdown_dark_code_blocks,
                                    )

                    with Card(elevation=1, margin=EdgeInsets.only(bottom=12)):
                        with Padding(EdgeInsets.all(14)):
                            with Column(cross_axis_alignment=CrossAxisAlignment.stretch):
                                _section_title("技能")
                                with Padding(EdgeInsets.only(top=8)):
                                    _switch_tile(
                                        "使用 Vibe Coding Skill",
                                        "开启后会从插件 assets 读取内置提示词，并支持 @file 与 @board 文件上下文。",
                                        data.settings_use_vibe_skill,
                                        data.settings_use_vibe_skill,
                                    )

                    with Card(elevation=1, margin=EdgeInsets.only(bottom=12)):
                        with Padding(EdgeInsets.all(14)):
                            with Column(cross_axis_alignment=CrossAxisAlignment.stretch):
                                _section_title("安全")
                                with Padding(EdgeInsets.only(top=8)):
                                    _switch_tile(
                                        "校验 TLS 证书",
                                        "仅在可信代理或本地测试证书场景下关闭。",
                                        data.settings_verify_tls,
                                        data.settings_verify_tls,
                                    )

                    with Card(elevation=1, margin=EdgeInsets.only(bottom=12)):
                        with Padding(EdgeInsets.all(14)):
                            Text(
                                ["状态：", status, "\n技能：", vibe_skill_status],
                                style=TextStyle(font_size=12),
                                soft_wrap=True,
                            )

                    with Padding(EdgeInsets.only(top=2)):
                        with Row(cross_axis_alignment=CrossAxisAlignment.center):
                            Spacer()
                            with ElevatedButton(
                                on_pressed=Event(
                                    lambda url="", api_key="", model="", verify_tls=DEFAULT_VERIFY_TLS, auto_process_url=DEFAULT_AUTO_PROCESS_URL, thinking_enabled=DEFAULT_THINKING_ENABLED, reasoning_effort=DEFAULT_REASONING_EFFORT, use_vibe_skill=DEFAULT_USE_VIBE_SKILL, markdown_code_font_family="", markdown_dark_code_blocks=DEFAULT_MARKDOWN_DARK_CODE_BLOCKS, **_: plugin.save_settings(
                                        url,
                                        api_key,
                                        model,
                                        verify_tls,
                                        auto_process_url,
                                        thinking_enabled,
                                        reasoning_effort,
                                        use_vibe_skill,
                                        markdown_code_font_family,
                                        markdown_dark_code_blocks,
                                    ),
                                    args={
                                        "url": data.settings_url,
                                        "api_key": data.settings_api_key,
                                        "model": data.settings_model,
                                        "verify_tls": data.settings_verify_tls,
                                        "auto_process_url": data.settings_auto_process_url,
                                        "thinking_enabled": data.settings_thinking_enabled,
                                        "reasoning_effort": data.settings_reasoning_effort,
                                        "use_vibe_skill": data.settings_use_vibe_skill,
                                        "markdown_code_font_family": data.settings_markdown_code_font_family,
                                        "markdown_dark_code_blocks": data.settings_markdown_dark_code_blocks,
                                    },
                                )
                            ):
                                Text("保存")
    return page

class AiChatPlugin(UiPlugin):
    def __init__(self):
        super().__init__()
        self.api_url = DEFAULT_API_URL
        self.api_key = ""
        self.model = DEFAULT_MODEL
        self.verify_tls = DEFAULT_VERIFY_TLS
        self.auto_process_url = DEFAULT_AUTO_PROCESS_URL
        self.thinking_enabled = DEFAULT_THINKING_ENABLED
        self.reasoning_effort = DEFAULT_REASONING_EFFORT
        self.use_vibe_skill = DEFAULT_USE_VIBE_SKILL
        self.markdown_code_font_family = DEFAULT_MARKDOWN_CODE_FONT_FAMILY
        self.markdown_dark_code_blocks = DEFAULT_MARKDOWN_DARK_CODE_BLOCKS
        self.vibe_skill_prompt = ""
        self.vibe_skill_status = "Vibe Coding Skill 尚未加载。"
        self.messages: list[dict[str, Any]] = []
        self.status = "请在设置中填写 API 密钥。"
        self.is_streaming = False
        self._lock = threading.RLock()
        self._last_refresh_at = 0.0
        self.pages = {}
        self._render()

    def on_start(self):
        print("AI 对话插件已启动")
        self.router.goto("home")
        self._load_settings()
        self.path.get(
            PathScope.ASSETS,
            callback=lambda **response: self._after_assets_path(response),
        )

    def on_refresh(self):
        self._render()

    def on_dispose(self):
        print("AI 对话插件已释放")

    def _render(self):
        with self._lock:
            visible_messages = [
                {**dict(item), "_index": index}
                for index, item in enumerate(self.messages)
                if item.get("visible", True) is not False
            ]
            messages = visible_messages
            is_streaming = self.is_streaming
            api_url = self.api_url
            api_key = self.api_key
            model = self.model
            verify_tls = self.verify_tls
            auto_process_url = self.auto_process_url
            thinking_enabled = self.thinking_enabled
            reasoning_effort = self.reasoning_effort
            use_vibe_skill = self.use_vibe_skill
            markdown_code_font_family = self.markdown_code_font_family
            markdown_dark_code_blocks = self.markdown_dark_code_blocks
            vibe_skill_status = self.vibe_skill_status
        self.pages = {
            "home": build_home_page(
                messages,
                is_streaming,
                markdown_code_font_family,
                markdown_dark_code_blocks,
            ),
            "settings": build_settings_page(
                api_url,
                api_key,
                model,
                verify_tls,
                auto_process_url,
                thinking_enabled,
                reasoning_effort,
                use_vibe_skill,
                markdown_code_font_family,
                markdown_dark_code_blocks,
                self.status,
                vibe_skill_status,
            ),
        }

    def toggle_reasoning(self, index: int = -1):
        with self._lock:
            if index < 0 or index >= len(self.messages):
                return
            message = self.messages[index]
            if message.get("role") != "assistant":
                return
            if not message.get("reasoning_content"):
                return
            message["show_reasoning"] = not bool(message.get("show_reasoning"))
        self._refresh_pages(force=True)

    def _refresh_pages(self, force: bool = False):
        now = time.monotonic()
        if not force and now - self._last_refresh_at < REFRESH_INTERVAL:
            return
        self._last_refresh_at = now
        self._render()
        if self.bridge.asyncio_loop is not None:
            self.bridge.refresh(call_on_refresh=False)

    def _set_status(self, status: str, force: bool = True):
        with self._lock:
            self.status = status
        self._refresh_pages(force=force)

    def _load_settings(self):
        self.persistence.get(
            CONFIG_GROUP,
            "url",
            callback=lambda data=None, **_: self._apply_loaded_url(data),
        )
        self.persistence.get(
            CONFIG_GROUP,
            "api_key",
            callback=lambda data=None, **_: self._apply_loaded_api_key(data),
        )
        self.persistence.get(
            CONFIG_GROUP,
            "model",
            callback=lambda data=None, **_: self._apply_loaded_model(data),
        )
        self.persistence.get(
            CONFIG_GROUP,
            "verify_tls",
            callback=lambda data=None, **_: self._apply_loaded_verify_tls(data),
        )
        self.persistence.get(
            CONFIG_GROUP,
            "auto_process_url",
            callback=lambda data=None, **_: self._apply_loaded_auto_process_url(data),
        )
        self.persistence.get(
            CONFIG_GROUP,
            "thinking_enabled",
            callback=lambda data=None, **_: self._apply_loaded_thinking_enabled(data),
        )
        self.persistence.get(
            CONFIG_GROUP,
            "reasoning_effort",
            callback=lambda data=None, **_: self._apply_loaded_reasoning_effort(data),
        )
        self.persistence.get(
            CONFIG_GROUP,
            "use_vibe_skill",
            callback=lambda data=None, **_: self._apply_loaded_use_vibe_skill(data),
        )
        self.persistence.get(
            CONFIG_GROUP,
            "markdown_code_font_family",
            callback=lambda data=None, **_: self._apply_loaded_markdown_code_font_family(data),
        )
        self.persistence.get(
            CONFIG_GROUP,
            "markdown_dark_code_blocks",
            callback=lambda data=None, **_: self._apply_loaded_markdown_dark_code_blocks(data),
        )

    def _apply_loaded_url(self, value: Any):
        with self._lock:
            self.api_url = _coerce_text(value, DEFAULT_API_URL)
        self.bridge.let(data.settings_url, self.api_url)
        self._refresh_pages(force=True)

    def _apply_loaded_api_key(self, value: Any):
        with self._lock:
            self.api_key = _coerce_text(value, "", allow_empty=True)
        self.bridge.let(data.settings_api_key, self.api_key)
        self._set_status(
            "已就绪。" if self.api_key else "请在设置中填写 API 密钥。",
            force=True,
        )

    def _apply_loaded_model(self, value: Any):
        with self._lock:
            self.model = _coerce_text(value, DEFAULT_MODEL)
        self.bridge.let(data.settings_model, self.model)
        self._refresh_pages(force=True)

    def _apply_loaded_verify_tls(self, value: Any):
        with self._lock:
            self.verify_tls = _coerce_bool(value, DEFAULT_VERIFY_TLS)
        self.bridge.let(data.settings_verify_tls, self.verify_tls)
        self._refresh_pages(force=True)

    def _apply_loaded_auto_process_url(self, value: Any):
        with self._lock:
            self.auto_process_url = _coerce_bool(value, DEFAULT_AUTO_PROCESS_URL)
        self.bridge.let(data.settings_auto_process_url, self.auto_process_url)
        self._refresh_pages(force=True)

    def _apply_loaded_thinking_enabled(self, value: Any):
        with self._lock:
            self.thinking_enabled = _coerce_bool(value, DEFAULT_THINKING_ENABLED)
        self.bridge.let(data.settings_thinking_enabled, self.thinking_enabled)
        self._refresh_pages(force=True)

    def _apply_loaded_reasoning_effort(self, value: Any):
        with self._lock:
            self.reasoning_effort = _normalize_reasoning_effort(
                value,
                DEFAULT_REASONING_EFFORT,
            )
        self.bridge.let(data.settings_reasoning_effort, self.reasoning_effort)
        self._refresh_pages(force=True)

    def _apply_loaded_use_vibe_skill(self, value: Any):
        with self._lock:
            self.use_vibe_skill = _coerce_bool(value, DEFAULT_USE_VIBE_SKILL)
        self.bridge.let(data.settings_use_vibe_skill, self.use_vibe_skill)
        self._refresh_pages(force=True)

    def _apply_loaded_markdown_code_font_family(self, value: Any):
        with self._lock:
            self.markdown_code_font_family = _coerce_text(
                value,
                DEFAULT_MARKDOWN_CODE_FONT_FAMILY,
                allow_empty=True,
            )
        self.bridge.let(
            data.settings_markdown_code_font_family,
            self.markdown_code_font_family,
        )
        self._refresh_pages(force=True)

    def _apply_loaded_markdown_dark_code_blocks(self, value: Any):
        with self._lock:
            self.markdown_dark_code_blocks = _coerce_bool(
                value,
                DEFAULT_MARKDOWN_DARK_CODE_BLOCKS,
            )
        self.bridge.let(
            data.settings_markdown_dark_code_blocks,
            self.markdown_dark_code_blocks,
        )
        self._refresh_pages(force=True)

    def _after_assets_path(self, response: dict[str, Any]):
        assets_path = response.get("path") or response.get("data") or self.assets
        self._load_vibe_skill_prompt(assets_path)

    def _load_vibe_skill_prompt(self, assets_path: Any = None):
        base_path = Path(assets_path) if assets_path else self.assets
        if base_path is None:
            with self._lock:
                self.vibe_skill_prompt = ""
                self.vibe_skill_status = "未获取插件 assets 路径。"
            self._refresh_pages(force=True)
            return

        skill_path = Path(base_path) / VIBE_SKILL_RELATIVE_PATH
        try:
            skill_prompt = skill_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            with self._lock:
                self.vibe_skill_prompt = ""
                self.vibe_skill_status = f"加载 Vibe Coding Skill 失败：{exc}"
            self._refresh_pages(force=True)
            return

        with self._lock:
            self.vibe_skill_prompt = skill_prompt
            self.vibe_skill_status = "Vibe Coding Skill 已加载。"
        self._refresh_pages(force=True)

    def save_settings(
        self,
        url: str = "",
        api_key: str = "",
        model: str = "",
        verify_tls: Any = DEFAULT_VERIFY_TLS,
        auto_process_url: Any = DEFAULT_AUTO_PROCESS_URL,
        thinking_enabled: Any = DEFAULT_THINKING_ENABLED,
        reasoning_effort: str = DEFAULT_REASONING_EFFORT,
        use_vibe_skill: Any = DEFAULT_USE_VIBE_SKILL,
        markdown_code_font_family: str = DEFAULT_MARKDOWN_CODE_FONT_FAMILY,
        markdown_dark_code_blocks: Any = DEFAULT_MARKDOWN_DARK_CODE_BLOCKS,
    ):
        next_url = _coerce_text(url, DEFAULT_API_URL)
        next_key = _coerce_text(api_key, "", allow_empty=True)
        next_model = _coerce_text(model, DEFAULT_MODEL)
        next_verify_tls = _coerce_bool(verify_tls, DEFAULT_VERIFY_TLS)
        next_auto_process_url = _coerce_bool(
            auto_process_url, DEFAULT_AUTO_PROCESS_URL
        )
        next_thinking_enabled = _coerce_bool(
            thinking_enabled, DEFAULT_THINKING_ENABLED
        )
        next_reasoning_effort = _normalize_reasoning_effort(
            reasoning_effort,
            DEFAULT_REASONING_EFFORT,
        )
        next_use_vibe_skill = _coerce_bool(use_vibe_skill, DEFAULT_USE_VIBE_SKILL)
        next_markdown_code_font_family = _coerce_text(
            markdown_code_font_family,
            DEFAULT_MARKDOWN_CODE_FONT_FAMILY,
            allow_empty=True,
        )
        next_markdown_dark_code_blocks = _coerce_bool(
            markdown_dark_code_blocks,
            DEFAULT_MARKDOWN_DARK_CODE_BLOCKS,
        )
        with self._lock:
            self.api_url = next_url
            self.api_key = next_key
            self.model = next_model
            self.verify_tls = next_verify_tls
            self.auto_process_url = next_auto_process_url
            self.thinking_enabled = next_thinking_enabled
            self.reasoning_effort = next_reasoning_effort
            self.use_vibe_skill = next_use_vibe_skill
            self.markdown_code_font_family = next_markdown_code_font_family
            self.markdown_dark_code_blocks = next_markdown_dark_code_blocks
            self.status = "设置已保存。" if next_key else "API 密钥为空。"
        self.persistence.set(CONFIG_GROUP, "url", next_url)
        self.persistence.set(CONFIG_GROUP, "api_key", next_key)
        self.persistence.set(CONFIG_GROUP, "model", next_model)
        self.persistence.set(CONFIG_GROUP, "verify_tls", next_verify_tls)
        self.persistence.set(
            CONFIG_GROUP, "auto_process_url", next_auto_process_url
        )
        self.persistence.set(
            CONFIG_GROUP, "thinking_enabled", next_thinking_enabled
        )
        self.persistence.set(
            CONFIG_GROUP, "reasoning_effort", next_reasoning_effort
        )
        self.persistence.set(CONFIG_GROUP, "use_vibe_skill", next_use_vibe_skill)
        self.persistence.set(
            CONFIG_GROUP,
            "markdown_code_font_family",
            next_markdown_code_font_family,
        )
        self.persistence.set(
            CONFIG_GROUP,
            "markdown_dark_code_blocks",
            next_markdown_dark_code_blocks,
        )
        self.bridge.let(data.settings_url, next_url)
        self.bridge.let(data.settings_api_key, next_key)
        self.bridge.let(data.settings_model, next_model)
        self.bridge.let(data.settings_verify_tls, next_verify_tls)
        self.bridge.let(data.settings_auto_process_url, next_auto_process_url)
        self.bridge.let(data.settings_thinking_enabled, next_thinking_enabled)
        self.bridge.let(data.settings_reasoning_effort, next_reasoning_effort)
        self.bridge.let(data.settings_use_vibe_skill, next_use_vibe_skill)
        self.bridge.let(
            data.settings_markdown_code_font_family,
            next_markdown_code_font_family,
        )
        self.bridge.let(
            data.settings_markdown_dark_code_blocks,
            next_markdown_dark_code_blocks,
        )
        self._refresh_pages(force=True)

    def _callback_error_message(self, response: dict[str, Any]) -> str:
        message = response.get("message")
        if message:
            return str(message)
        code = response.get("code")
        if code:
            return str(code)
        return ""

    def _show_apply_error(self, detail: str):
        message = f"应用 diff 失败：{detail}"
        self._set_status(message)
        self.message.error(message)

    def _show_apply_success(self, path: str):
        message = f"已应用 diff：{path}"
        self._set_status(message)
        self.message.success(message)

    def apply_diff(self, path: str = "", diff: str = ""):
        path = (path or "").strip()
        diff = diff or ""
        if not path:
            self._show_apply_error("缺少文件路径")
            return
        if not diff.strip():
            self._show_apply_error("diff 内容为空")
            return
        self._set_status(f"正在应用 diff：{path}")
        if _is_absolute_diff_path(path):
            self._open_diff_path(path, path, diff)
            return
        self.file.get_root_dir(
            callback=lambda **response: self._after_get_root_for_diff(
                path,
                diff,
                response,
            )
        )

    def _after_get_root_for_diff(
        self,
        display_path: str,
        diff: str,
        response: dict[str, Any],
    ):
        error = self._callback_error_message(response)
        if error:
            self._show_apply_error(error)
            return
        try:
            editor_path = _resolve_diff_path(display_path, response.get("data"))
        except Exception as exc:
            self._show_apply_error(str(exc))
            return
        self._open_diff_path(display_path, editor_path, diff)

    def _open_diff_path(self, display_path: str, editor_path: str, diff: str):
        self.editor.open_file(
            editor_path,
            callback=lambda **response: self._after_open_diff(
                display_path,
                diff,
                response,
            ),
        )

    def _after_open_diff(self, path: str, diff: str, response: dict[str, Any]):
        error = self._callback_error_message(response)
        if error:
            self._show_apply_error(error)
            return
        self.editor.get_text(
            callback=lambda **text_response: self._apply_diff_to_open_file(
                path,
                diff,
                text_response,
            )
        )

    def _apply_diff_to_open_file(
        self,
        path: str,
        diff: str,
        response: dict[str, Any],
    ):
        error = self._callback_error_message(response)
        if error:
            self._show_apply_error(error)
            return
        original_text = response.get("data")
        if not isinstance(original_text, str):
            self._show_apply_error("无法读取当前编辑器文本")
            return
        try:
            updated_text = _apply_unified_diff(original_text, diff, path)
        except Exception as exc:
            self._show_apply_error(str(exc))
            self._retry_diff_after_apply_failure(path, diff, original_text, str(exc))
            return
        self.editor.set_text(
            updated_text,
            callback=lambda **set_response: self._after_set_diff(path, set_response),
        )

    def _after_set_diff(self, path: str, response: dict[str, Any]):
        error = self._callback_error_message(response)
        if error:
            self._show_apply_error(error)
            return
        self._show_apply_success(path)

    def _retry_diff_after_apply_failure(
        self,
        path: str,
        diff: str,
        original_text: str,
        error: str,
    ):
        with self._lock:
            if self.is_streaming or not self.api_key:
                return
            self.is_streaming = True
            failures = [
                {
                    "path": path,
                    "diff": diff,
                    "error": error,
                    "original_text": original_text,
                }
            ]
            self.messages.append(
                {
                    "role": "notice",
                    "content": _diff_validation_failure_notice(failures, 0),
                }
            )
            self.messages.append(
                {
                    "role": "user",
                    "content": "",
                    "request_content": _format_diff_repair_prompt(failures, 1),
                    "visible": False,
                }
            )
            self.messages.append(_assistant_message())
            assistant_index = len(self.messages) - 1
            request_messages = self._request_messages_locked()
            self.status = "正在根据应用失败错误重试..."
        self._refresh_pages(force=True)
        thread = threading.Thread(
            target=self._stream_response,
            args=(request_messages, assistant_index, 1),
            daemon=True,
        )
        thread.start()

    def _validate_ai_diff_blocks(
        self,
        blocks: list[dict[str, str]],
        diff_retry_round: int,
        assistant_index: int = -1,
    ):
        needs_root = any(not _is_absolute_diff_path(block["path"]) for block in blocks)
        if not needs_root:
            self._validate_next_ai_diff_block(
                blocks,
                0,
                [],
                None,
                "",
                diff_retry_round,
                assistant_index,
            )
            return
        self.file.get_root_dir(
            callback=lambda **response: self._after_get_root_for_diff_validation(
                blocks,
                diff_retry_round,
                assistant_index,
                response,
            )
        )

    def _after_get_root_for_diff_validation(
        self,
        blocks: list[dict[str, str]],
        diff_retry_round: int,
        assistant_index: int,
        response: dict[str, Any],
    ):
        root_error = self._callback_error_message(response)
        root_dir = None if root_error else response.get("data")
        self._validate_next_ai_diff_block(
            blocks,
            0,
            [],
            root_dir,
            root_error,
            diff_retry_round,
            assistant_index,
        )

    def _validate_next_ai_diff_block(
        self,
        blocks: list[dict[str, str]],
        index: int,
        failures: list[dict[str, Any]],
        root_dir: str | None,
        root_error: str,
        diff_retry_round: int,
        assistant_index: int,
    ):
        if index >= len(blocks):
            self._after_diff_validation_complete(
                blocks,
                failures,
                diff_retry_round,
                assistant_index,
            )
            return

        block = blocks[index]
        path = block["path"]
        diff = block["diff"]
        try:
            if _is_absolute_diff_path(path):
                editor_path = path
            elif root_error:
                raise ValueError(f"无法获取项目根目录：{root_error}")
            else:
                editor_path = _resolve_diff_path(path, root_dir)
        except Exception as exc:
            failures.append(
                {
                    "path": path,
                    "diff": diff,
                    "error": str(exc),
                    "read_error": str(exc),
                }
            )
            self._validate_next_ai_diff_block(
                blocks,
                index + 1,
                failures,
                root_dir,
                root_error,
                diff_retry_round,
                assistant_index,
            )
            return

        self.file.read_file(
            editor_path,
            callback=lambda **response: self._after_read_diff_validation_file(
                blocks,
                index,
                failures,
                root_dir,
                root_error,
                diff_retry_round,
                assistant_index,
                path,
                diff,
                response,
            ),
        )

    def _after_read_diff_validation_file(
        self,
        blocks: list[dict[str, str]],
        index: int,
        failures: list[dict[str, Any]],
        root_dir: str | None,
        root_error: str,
        diff_retry_round: int,
        assistant_index: int,
        path: str,
        diff: str,
        response: dict[str, Any],
    ):
        read_error = self._callback_error_message(response)
        original_text = response.get("data")
        if not isinstance(original_text, str):
            if _diff_declares_new_file(diff):
                original_text = ""
            else:
                failures.append(
                    {
                        "path": path,
                        "diff": diff,
                        "error": read_error or "无法读取当前文件，不能校验 diff",
                        "read_error": read_error or "无法读取当前文件",
                    }
                )
                self._validate_next_ai_diff_block(
                    blocks,
                    index + 1,
                    failures,
                    root_dir,
                    root_error,
                    diff_retry_round,
                    assistant_index,
                )
                return

        try:
            _apply_unified_diff(original_text, diff, path)
        except Exception as exc:
            failures.append(
                {
                    "path": path,
                    "diff": diff,
                    "error": str(exc),
                    "original_text": original_text,
                }
            )

        self._validate_next_ai_diff_block(
            blocks,
            index + 1,
            failures,
            root_dir,
            root_error,
            diff_retry_round,
            assistant_index,
        )

    def _after_diff_validation_complete(
        self,
        blocks: list[dict[str, str]],
        failures: list[dict[str, Any]],
        diff_retry_round: int,
        assistant_index: int,
    ):
        if not failures:
            with self._lock:
                notice = _diff_validation_success_notice(blocks)
                # Keep a valid diff attached to the assistant message that produced it.
                if 0 <= assistant_index < len(self.messages):
                    self.messages[assistant_index]["diff_validation_notice"] = notice
                else:
                    self.messages.append({"role": "notice", "content": notice})
                self.status = "Diff 已通过预检。"
                self.is_streaming = False
            self._refresh_pages(force=True)
            return

        notice = _diff_validation_failure_notice(failures, diff_retry_round)
        if diff_retry_round >= MAX_DIFF_REPAIR_ROUNDS:
            with self._lock:
                self.messages.append({"role": "notice", "content": notice})
                self.status = "Diff 预检失败，已达到自动重试上限。"
                self.is_streaming = False
            self._refresh_pages(force=True)
            return

        repair_prompt = _format_diff_repair_prompt(failures, diff_retry_round + 1)
        with self._lock:
            self.messages.append({"role": "notice", "content": notice})
            self.messages.append(
                {
                    "role": "user",
                    "content": "",
                    "request_content": repair_prompt,
                    "visible": False,
                }
            )
            self.messages.append(_assistant_message())
            assistant_index = len(self.messages) - 1
            request_messages = self._request_messages_locked()
            self.status = "正在根据 diff 预检错误重试..."
        self._refresh_pages(force=True)
        thread = threading.Thread(
            target=self._stream_response,
            args=(request_messages, assistant_index, diff_retry_round + 1),
            daemon=True,
        )
        thread.start()

    def clear_chat(self):
        if self.is_streaming:
            self._set_status("请等待当前回答完成。")
            return
        with self._lock:
            self.messages.clear()
            self.status = "已就绪。" if self.api_key else "请在设置中填写 API 密钥。"
        self.bridge.let(data.prompt, "")
        self._refresh_pages(force=True)

    def send_prompt(self, prompt: str = ""):
        prompt = (prompt or "").strip()
        if not prompt:
            self._set_status("请先输入消息。")
            return
        workspace_refs = _extract_workspace_refs(prompt)
        with self._lock:
            if self.is_streaming:
                self.status = "请等待当前回答完成。"
                self._refresh_pages(force=True)
                return
            if not self.api_key:
                self.status = "请在设置中填写 API 密钥。"
                self._refresh_pages(force=True)
                return
            self.is_streaming = True
            self.status = "正在读取工作区文件..." if workspace_refs else "正在生成回答..."
        self.bridge.let(data.prompt, "")
        self._refresh_pages(force=True)
        if workspace_refs:
            self._read_workspace_refs(prompt, workspace_refs, 0, [])
            return
        self._start_prompt_stream(prompt, prompt)

    def _read_workspace_refs(
        self,
        prompt: str,
        refs: list[dict[str, str]],
        index: int,
        results: list[dict[str, Any]],
        on_complete: Callable[[list[dict[str, Any]]], None] | None = None,
    ):
        if index >= len(refs):
            if on_complete is not None:
                on_complete(results)
                return
            workspace_context = _format_workspace_context(results)
            request_prompt = (
                f"{workspace_context}\n\n用户请求：\n{prompt}" if workspace_context else prompt
            )
            self._start_prompt_stream(prompt, request_prompt, results)
            return

        ref = refs[index]
        source = ref["source"]
        path = ref["path"]
        if source == "board":
            self.board.read_file(
                path,
                callback=lambda **response: self._after_workspace_ref_read(
                    prompt,
                    refs,
                    index,
                    results,
                    source,
                    path,
                    response,
                    on_complete,
                ),
            )
            return

        if _is_absolute_diff_path(path):
            self.file.read_file(
                path,
                callback=lambda **response: self._after_workspace_ref_read(
                    prompt,
                    refs,
                    index,
                    results,
                    source,
                    path,
                    response,
                    on_complete,
                ),
            )
            return

        self.file.get_root_dir(
            callback=lambda **response: self._after_workspace_root(
                prompt,
                refs,
                index,
                results,
                path,
                response,
                on_complete,
            )
        )

    def _after_workspace_root(
        self,
        prompt: str,
        refs: list[dict[str, str]],
        index: int,
        results: list[dict[str, Any]],
        path: str,
        response: dict[str, Any],
        on_complete: Callable[[list[dict[str, Any]]], None] | None = None,
    ):
        error = self._callback_error_message(response)
        if error:
            results.append({"source": "file", "path": path, "error": error})
            self._read_workspace_refs(prompt, refs, index + 1, results, on_complete)
            return
        try:
            resolved_path = _resolve_diff_path(path, response.get("data"))
        except Exception as exc:
            results.append({"source": "file", "path": path, "error": str(exc)})
            self._read_workspace_refs(prompt, refs, index + 1, results, on_complete)
            return
        self.file.read_file(
            resolved_path,
            callback=lambda **read_response: self._after_workspace_ref_read(
                prompt,
                refs,
                index,
                results,
                "file",
                path,
                read_response,
                on_complete,
            ),
        )

    def _after_workspace_ref_read(
        self,
        prompt: str,
        refs: list[dict[str, str]],
        index: int,
        results: list[dict[str, Any]],
        source: str,
        path: str,
        response: dict[str, Any],
        on_complete: Callable[[list[dict[str, Any]]], None] | None = None,
    ):
        error = self._callback_error_message(response)
        content = response.get("data")
        if isinstance(content, str):
            results.append(
                {
                    "source": source,
                    "path": path,
                    "content": content,
                }
            )
        else:
            results.append(
                {
                    "source": source,
                    "path": path,
                    "error": error or "无法读取文件内容",
                }
            )
        self._read_workspace_refs(prompt, refs, index + 1, results, on_complete)

    def _start_prompt_stream(
        self,
        display_prompt: str,
        request_prompt: str,
        workspace_results: list[dict[str, Any]] | None = None,
    ):
        with self._lock:
            self.messages.append(
                {
                    "role": "user",
                    "content": display_prompt,
                    "request_content": request_prompt,
                }
            )
            notice = _workspace_read_notice(workspace_results or [])
            if notice:
                self.messages.append({"role": "notice", "content": notice})
            self.messages.append(_assistant_message())
            assistant_index = len(self.messages) - 1
            request_messages = self._request_messages_locked()
            self.status = "正在生成回答..."
        self._refresh_pages(force=True)
        thread = threading.Thread(
            target=self._stream_response,
            args=(request_messages, assistant_index, 0),
            daemon=True,
        )
        thread.start()

    def _continue_after_ai_read(
        self,
        results: list[dict[str, Any]],
    ):
        workspace_context = _format_workspace_context(results)
        request_content = (
            f"{workspace_context}\n\n请基于已读取文件继续回答。"
            if workspace_context
            else "文件读取失败。请说明缺少的上下文，并基于已有信息继续回答。"
        )
        with self._lock:
            notice = _workspace_read_notice(results)
            if notice:
                self.messages.append({"role": "notice", "content": notice})
            self.messages.append(
                {
                    "role": "user",
                    "content": "",
                    "request_content": request_content,
                    "visible": False,
                }
            )
            self.messages.append(_assistant_message())
            assistant_index = len(self.messages) - 1
            request_messages = self._request_messages_locked()
            self.status = "正在基于读取文件继续生成..."
        self._refresh_pages(force=True)
        thread = threading.Thread(
            target=self._stream_response,
            args=(request_messages, assistant_index, 0),
            daemon=True,
        )
        thread.start()

    def _request_messages_locked(self) -> list[dict[str, str]]:
        request_messages: list[dict[str, str]] = []
        for message in self.messages:
            role = message.get("role", "")
            content = (
                message.get("request_content") or message.get("content") or ""
            ).strip()
            if role not in {"user", "assistant"} or not content:
                continue
            request_messages.append({"role": role, "content": content})
        return request_messages

    def _stream_response(
        self,
        request_messages: list[dict[str, str]],
        assistant_index: int,
        diff_retry_round: int = 0,
    ):
        received = False
        try:
            for delta in self._iter_response_stream(request_messages):
                content_delta = delta.get("content") or ""
                reasoning_delta = delta.get("reasoning") or ""
                if not content_delta and not reasoning_delta:
                    continue
                received = True
                with self._lock:
                    if assistant_index < len(self.messages):
                        if content_delta:
                            self.messages[assistant_index]["content"] += content_delta
                        if reasoning_delta:
                            self.messages[assistant_index]["reasoning_content"] += (
                                reasoning_delta
                            )
                self._refresh_pages()
            read_refs: list[dict[str, str]] = []
            diff_blocks: list[dict[str, str]] = []
            with self._lock:
                if not received and assistant_index < len(self.messages):
                    self.messages[assistant_index]["content"] = "未收到文本输出。"
                if received and assistant_index < len(self.messages):
                    read_refs = _extract_ai_read_refs(
                        self.messages[assistant_index].get("content", "")
                    )
                if read_refs and assistant_index < len(self.messages):
                    self.messages[assistant_index]["content"] = _ai_read_request_notice(
                        read_refs
                    )
                    self.status = "AI 正在读取文件..."
                else:
                    diff_blocks = (
                        _extract_diff_blocks(
                            self.messages[assistant_index].get("content", "")
                        )
                        if received and assistant_index < len(self.messages)
                        else []
                    )
                    if diff_blocks:
                        self.status = "正在预检 diff..."
                    else:
                        self.status = "完成。"
                        self.is_streaming = False
            if read_refs:
                self._refresh_pages(force=True)
                self._read_workspace_refs(
                    "",
                    read_refs,
                    0,
                    [],
                    on_complete=lambda results: self._continue_after_ai_read(results),
                )
                return
            if diff_blocks:
                self._refresh_pages(force=True)
                self._validate_ai_diff_blocks(
                    diff_blocks,
                    diff_retry_round,
                    assistant_index,
                )
                return
            self._refresh_pages(force=True)
        except Exception as exc:
            with self._lock:
                if assistant_index < len(self.messages):
                    self.messages[assistant_index]["content"] = f"请求失败：{exc}"
                self.status = "生成回答时出错。"
                self.is_streaming = False
            self._refresh_pages(force=True)

    def _system_prompt(self) -> str:
        with self._lock:
            use_vibe_skill = self.use_vibe_skill
            vibe_skill_prompt = self.vibe_skill_prompt
        if use_vibe_skill and vibe_skill_prompt.strip():
            return f"{SYSTEM_PROMPT}\n\n# 内置 Skill: vibe-coding\n{vibe_skill_prompt.strip()}"
        return SYSTEM_PROMPT

    def _iter_response_stream(
        self,
        request_messages: list[dict[str, str]],
    ) -> Iterable[dict[str, str]]:
        with self._lock:
            api_url = self.api_url
            api_key = self.api_key
            model = self.model
            verify_tls = self.verify_tls
            auto_process_url = self.auto_process_url
            thinking_enabled = self.thinking_enabled
            reasoning_effort = self.reasoning_effort
        system_prompt = self._system_prompt()
        endpoint_url = _endpoint_url(api_url, auto_process_url)
        payload = self._chat_completion_payload(
            model,
            system_prompt,
            request_messages,
            thinking_enabled,
            reasoning_effort,
        )
        yield from self._stream_chat_completion(
            endpoint_url,
            api_key,
            payload,
            verify_tls,
        )

    def _chat_completion_payload(
        self,
        model: str,
        system_prompt: str,
        request_messages: list[dict[str, str]],
        thinking_enabled: bool,
        reasoning_effort: str,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                *request_messages,
            ],
            "stream": True,
        }
        if thinking_enabled:
            extra_body: dict[str, Any] = {
                "thinking": {"type": "enabled"},
            }
            if reasoning_effort:
                extra_body["reasoning_effort"] = reasoning_effort
            payload.update(extra_body)
        return payload

    def _stream_chat_completion(
        self,
        endpoint_url: str,
        api_key: str,
        payload: dict[str, Any],
        verify_tls: bool,
    ) -> Iterable[dict[str, str]]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            endpoint_url,
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
            method="POST",
        )
        context = None if verify_tls else ssl._create_unverified_context()
        try:
            with urllib.request.urlopen(request, context=context) as response:
                event_lines: list[str] = []
                for raw_line in response:
                    line = raw_line.decode("utf-8", errors="replace")
                    if line in {"", "\n", "\r\n"}:
                        yield from self._extract_sse_delta(event_lines)
                        event_lines = []
                    else:
                        event_lines.append(line.rstrip("\r\n"))
                if event_lines:
                    yield from self._extract_sse_delta(event_lines)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace").strip()
            raise RuntimeError(
                f"API 请求失败（HTTP {exc.code}）：{detail or exc.reason}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"API 请求失败：{exc.reason}") from exc

    def _extract_sse_delta(self, event_lines: list[str]) -> Iterable[dict[str, str]]:
        data_lines: list[str] = []
        for line in event_lines:
            if not line or line.startswith(":"):
                continue
            if line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
        if not data_lines:
            raw_event = "\n".join(event_lines).strip()
            data_lines = [raw_event] if raw_event.startswith("{") else []

        data_text = "\n".join(data_lines).strip()
        if not data_text or data_text == "[DONE]":
            return
        try:
            payload = json.loads(data_text)
        except json.JSONDecodeError:
            return
        delta = self._extract_stream_delta(payload)
        if delta.get("content") or delta.get("reasoning"):
            yield delta

    def _extract_stream_delta(self, payload: dict[str, Any]) -> dict[str, str]:
        choices = payload.get("choices", [])
        if not choices:
            content = payload.get("delta", "") or payload.get("text", "") or ""
            reasoning = (
                payload.get("reasoning_content", "")
                or payload.get("reasoning", "")
                or payload.get("reasoning_text", "")
                or ""
            )
            return {"content": str(content), "reasoning": str(reasoning)}

        first_choice = choices[0] if isinstance(choices[0], dict) else {}
        delta = first_choice.get("delta") or first_choice.get("message") or {}
        if not isinstance(delta, dict):
            return {"content": "", "reasoning": ""}
        content = delta.get("content", "") or ""
        reasoning = (
            delta.get("reasoning_content", "")
            or delta.get("reasoning", "")
            or delta.get("reasoning_text", "")
            or ""
        )
        return {"content": str(content), "reasoning": str(reasoning)}


plugin = None


def main():
    global plugin
    plugin = AiChatPlugin()
    plugin.start()


if __name__ == "__main__":
    main()
