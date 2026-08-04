import shutil
from pathlib import Path
from typing import Annotated, Dict, List, Literal, Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from .package_command import PackageCommand
from .utils.selector import interactive_select, interactive_multiselect
from .test_command import TestCommand
from sys import version

app = typer.Typer(
    name="pyrite-sdk",
    help="PyriteSDK 开发调试工具",
)

_console = Console()

PLATFORMS = ["Android", "Darwin", "Windows", "Linux"]
ARCH_MAP = {
    "Android": ["arm64-v8a", "armeabi-v7a", "x86_64"],
    "Darwin": ["arm64", "x86_64"],
    "Windows": [""],
    "Linux": [""],
}

__version__ = "1.0.0"


def version_callback(value: bool):
    if value:
        print(
            f"""PyriteSDK Version: {__version__}
with Python {version}
Use `pyrsdk --help` for more info"""
        )
        raise typer.Exit()


VERSION_OPTION = Annotated[
    bool,
    typer.Option(
        "--version",
        "-v",
        help="Show tool version and quit.",
        is_eager=True,
        callback=version_callback,
    ),
]


def _interactive_mode() -> dict:
    """Interactively collect packaging parameters from the user."""
    _console.print()
    _console.print(
        Panel.fit(
            "[bold cyan]Pyrite SDK Packager[/bold cyan]\n\n"
            "（选择配置选项，或直接回车接受默认值）",
            border_style="cyan",
        )
    )
    _console.print()

    params: Dict[str, object] = {}

    # Step 1: source directory
    _console.print("[bold]Step 1:[/bold] 源目录")
    source_dir = Prompt.ask(
        "  源目录路径",
        default="src",
    )
    params["source_dir"] = source_dir

    # Step 2: platform
    _console.print("\n[bold]Step 2:[/bold] 目标平台")
    params["platform"] = interactive_select(["all", *PLATFORMS], "请选择目标平台:")

    # Step 3: architecture
    available_archs = ARCH_MAP.get(params["platform"], [])
    if available_archs:
        params["arch"] = interactive_multiselect(
            available_archs, "请选择目标架构 (默认全选):", default_all=True
        )

    # Step 4: requirements
    _console.print(f"\n[bold]Step 4:[/bold] Python 依赖包")

    req_txt_input = Prompt.ask(
        "  requirements.txt 文件路径",
        default="src/requirements.txt",
    ).strip()

    req_package_input = Prompt.ask(
        "  要安装的包列表 (逗号分隔，例如 requests, numpy)",
        default="",
    )
    requirements = (
        [r.strip() for r in req_package_input.split(",") if r.strip()]
        if req_package_input.strip()
        else []
    )

    req_arg_input = Prompt.ask(
        "  pip选项（逗号分隔，例如 --pre 等）",
        default="",
    )
    pip_args = (
        [r.strip() for r in req_arg_input.split(",") if r.strip()]
        if req_arg_input.strip()
        else []
    )

    params["requirements_file"] = req_txt_input
    params["requirements"] = [*requirements, *pip_args]

    # Step 5: options
    _console.print(f"\n[bold]Step 5:[/bold] 打包选项")

    params["compile_app"] = Confirm.ask("  编译应用代码", default=False)
    params["compile_packages"] = Confirm.ask("  编译依赖包", default=False)
    params["cleanup"] = Confirm.ask("  执行清理", default=False)
    params["verbose"] = Confirm.ask("  详细输出", default=False)
    params["pip_tool"] = Prompt.ask(
        "  依赖安装工具 (uv/pip)",
        default="uv",
    )

    # Step 6: asset path
    _console.print(f"\n[bold]Step 6:[/bold] 输出路径")
    params["asset"] = Prompt.ask(
        "  资产输出路径",
        default="build/app.zip",
    )

    # Hidden defaults
    params["exclude"] = []
    params["skip_site_packages"] = False
    params["cleanup_app"] = False
    params["cleanup_app_files"] = []
    params["cleanup_packages"] = False
    params["cleanup_package_files"] = []

    # Summary
    _console.print()
    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="bold white", justify="right")
    summary.add_column(style="cyan")

    summary.add_row("源目录", str(params["source_dir"]))
    summary.add_row("平台", str(params["platform"]))
    summary.add_row("架构", ", ".join(params["arch"]) if params["arch"] else "默认")
    dependency_summary = [
        *([f"-r {params['requirements_file']}"] if params["requirements_file"] else []),
        *params["requirements"],
    ]
    summary.add_row(
        "依赖", ", ".join(dependency_summary) if dependency_summary else "无"
    )
    summary.add_row("编译应用", "是" if params["compile_app"] else "否")
    summary.add_row("编译包", "是" if params["compile_packages"] else "否")
    summary.add_row("清理", "是" if params["cleanup"] else "否")
    summary.add_row("详细输出", "是" if params["verbose"] else "否")
    summary.add_row("依赖工具", str(params.get("pip_tool", "uv")))
    summary.add_row("输出路径", str(params["asset"]))

    _console.print(
        Panel(
            summary,
            title="[bold]配置摘要[/bold]",
            border_style="yellow",
        )
    )

    if not Confirm.ask("\n确认执行打包?", default=True):
        _console.print("[yellow]已取消[/yellow]")
        raise typer.Exit()

    return params


def _build_requirements(
    requirements: Optional[List[str] | object],
    requirements_file: Optional[str | object],
) -> list[str]:
    result: list[str] = []
    if isinstance(requirements_file, str) and requirements_file:
        result.extend(["-r", requirements_file])
    if isinstance(requirements, list):
        result.extend(requirements)
    return result


@app.command("package")
def package(
    platform: Annotated[
        Optional[Literal["Android", "Darwin", "Windows", "Linux", "all", None]],
        typer.Option(
            "-p",
            "--platform",
            help="为特定平台安装依赖，例如 'Android'",
        ),
    ] = None,
    source_dir: Annotated[
        Optional[str],
        typer.Argument(help="源目录"),
    ] = None,
    arch: Annotated[
        Optional[List[str]],
        typer.Option(
            "--arch",
            help="仅为特定架构安装依赖（留空以安装所有支持的架构）",
        ),
    ] = None,
    requirements: Annotated[
        Optional[List[str]],
        typer.Option(
            "-r",
            "--requirements",
            help="要安装的依赖列表，允许任何 pip 选项",
        ),
    ] = None,
    requirements_file: Annotated[
        Optional[str],
        typer.Option(
            "-rf",
            "--requirements-file",
            help='依赖文件路径，等同于 -r "-r" -r "requirements.txt"',
        ),
    ] = None,
    asset: Annotated[
        Optional[str],
        typer.Option(
            "-a",
            "--asset",
            help="输出资产路径，相对于当前目录，用于将 Python 程序打包到其中",
        ),
    ] = None,
    exclude: Annotated[
        Optional[List[str]],
        typer.Option(
            "--exclude",
            help='要从应用包中排除的相对路径列表，例如 "assets,build"',
        ),
    ] = None,
    skip_site_packages: Annotated[
        bool,
        typer.Option(
            "--skip-site-packages",
            help="跳过站点包的安装",
        ),
    ] = False,
    compile_app: Annotated[
        bool,
        typer.Option(
            "--compile-app",
            help="在打包前编译 Python 应用程序",
        ),
    ] = False,
    compile_packages: Annotated[
        bool,
        typer.Option(
            "--compile-packages",
            help="在打包前编译应用程序包",
        ),
    ] = False,
    cleanup: Annotated[
        bool,
        typer.Option(
            "--cleanup",
            help="从不必要的文件和目录中清理应用和包",
        ),
    ] = False,
    cleanup_app: Annotated[
        bool,
        typer.Option(
            "--cleanup-app",
            help="从不必要的文件和目录中清理应用",
        ),
    ] = False,
    cleanup_app_files: Annotated[
        Optional[List[str]],
        typer.Option(
            "--cleanup-app-files",
            help="要删除的额外应用文件和目录的 glob 列表",
        ),
    ] = None,
    cleanup_packages: Annotated[
        bool,
        typer.Option(
            "--cleanup-packages",
            help="从不必要的文件和目录中清理包",
        ),
    ] = False,
    cleanup_package_files: Annotated[
        Optional[List[str]],
        typer.Option(
            "--cleanup-package-files",
            help="要删除的额外包文件和目录的 glob 列表",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            help="详细输出",
        ),
    ] = False,
    pip_tool: Annotated[
        Literal["pip", "uv"],
        typer.Option(
            "--pip-tool",
            help="依赖安装工具，可选 uv 或 pip",
        ),
    ] = "uv",
    interactive: Annotated[
        bool,
        typer.Option(
            "--interactive",
            "-i",
            help="使用交互模式逐步配置打包参数",
        ),
    ] = False,
) -> None:
    """将 Python 应用打包到 Flutter 资产中"""
    use_interactive = interactive or not platform or source_dir is None

    if use_interactive:
        params = _interactive_mode()
        source_dir = params.get("source_dir")
        platform = params["platform"]
        arch = params.get("arch", [])
        requirements = params.get("requirements")
        requirements_file = params.get("requirements_file")
        asset = params.get("asset")
        exclude = params.get("exclude", [])
        skip_site_packages = params.get("skip_site_packages", False)
        compile_app = params.get("compile_app", False)
        compile_packages = params.get("compile_packages", False)
        cleanup = params.get("cleanup", False)
        cleanup_app = params.get("cleanup_app", False)
        cleanup_app_files = params.get("cleanup_app_files", [])
        cleanup_packages = params.get("cleanup_packages", False)
        cleanup_package_files = params.get("cleanup_package_files", [])
        verbose = params.get("verbose", False)
        pip_tool = params.get("pip_tool", "uv")

    requirements_file = requirements_file or str(Path(source_dir) / "requirements.txt")
    print(f"使用依赖文件: {requirements_file}")

    cmd = PackageCommand()
    target_platforms = PLATFORMS if platform == "all" else [platform]
    resolved_requirements = _build_requirements(requirements, requirements_file)
    for target_platform in target_platforms:
        print("正在处理目标平台：", target_platform)
        cmd.run(
            source_dir=source_dir,
            platform=target_platform,
            arch=arch or [],
            requirements=resolved_requirements,
            asset=asset,
            exclude=exclude or [],
            skip_site_packages=skip_site_packages,
            compile_app=compile_app,
            compile_packages=compile_packages,
            cleanup=cleanup,
            cleanup_app=cleanup_app,
            cleanup_app_files=cleanup_app_files or [],
            cleanup_packages=cleanup_packages,
            cleanup_package_files=cleanup_package_files or [],
            verbose=verbose,
            pip_tool=pip_tool,
        )


@app.command("create")
def create(
    plugin_type: Annotated[
        Literal["ui", "service", "data"],
        typer.Argument(help="插件类型"),
    ] = "ui",
    dir: Annotated[
        Optional[str],
        typer.Argument(help="源目录"),
    ] = ".",
):
    src_path = Path(__file__).parent / "template" / plugin_type
    dst_path = Path(dir).resolve() / "src"
    template_files = sorted(
        (path for path in src_path.iterdir() if path.is_file()),
        key=lambda path: path.name,
    )
    conflicts = [
        dst_path / path.name
        for path in template_files
        if (dst_path / path.name).exists()
    ]
    if conflicts:
        names = ", ".join(path.name for path in conflicts)
        raise typer.BadParameter(
            f"destination already contains template files: {names}",
            param_hint="dir",
        )
    dst_path.mkdir(parents=True, exist_ok=True)
    print("Source path:", src_path)
    print(f"Creating template {plugin_type} plugin to", dst_path)
    for source in template_files:
        shutil.copy2(source, dst_path / source.name)
    print("Completed.")


@app.command("test")
def test_plugin(
    dir: Annotated[
        Optional[str],
        typer.Argument(help="源目录"),
    ] = ".",
    raw_output: Annotated[
        bool,
        typer.Option(
            "--raw-output",
            help="输出纯文本",
        ),
    ] = False,
):
    dst_path = Path(dir).resolve()
    TestCommand().run(dst_path, raw_output, _console)


@app.callback()  # 为所有子命令添加此选项
def common(version: VERSION_OPTION = False):
    pass


if __name__ == "__main__":
    app()
