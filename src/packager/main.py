from typing import Annotated, Dict, List, Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from .package_command import PackageCommand
from .utils.selector import interactive_select, interactive_multiselect

app = typer.Typer(
    name="pyrite-sdk",
    help="用于将 Python 应用打包以配合 serious_python 包的工具",
)

_console = Console()

PLATFORMS = ["Android", "iOS", "Darwin", "Windows", "Linux"]
ARCH_MAP = {
    "Android": ["arm64-v8a", "armeabi-v7a", "x86_64", "x86"],
    "iOS": [],
    "Darwin": ["arm64", "x86_64"],
    "Windows": [""],
    "Linux": [""],
}


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
        default=".",
    )
    params["source_dir"] = source_dir

    # Step 2: platform
    _console.print("\n[bold]Step 2:[/bold] 目标平台")
    params["platform"] = interactive_select(PLATFORMS, "请选择目标平台:")

    # Step 3: architecture
    available_archs = ARCH_MAP.get(params["platform"], [])
    params["arch"] = interactive_multiselect(available_archs, "请选择目标架构 (默认全选):", default_all=True)

    # Step 4: requirements
    _console.print(f"\n[bold]Step 4:[/bold] Python 依赖包")

    req_txt_input = Prompt.ask(
        "  requirements.txt 文件路径",
        default="",
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

    params["requirements"] = [
        f"-r{req_txt_input}" if req_txt_input else "",
        *requirements,
        *pip_args,
    ]

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
    summary.add_row("依赖", ", ".join(params["requirements"]) if params["requirements"] else "无")
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


@app.command()
def package(
    platform: Annotated[
        Optional[str],
        typer.Option(
            "-p",
            "--platform",
            help="为特定平台安装依赖，例如 'Android'",
        ),
    ] = "",
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
        str,
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
    use_interactive = interactive or (
        not platform
        and source_dir is None
        and not any([arch, requirements])
    )

    if use_interactive:
        params = _interactive_mode()
        cmd = PackageCommand()
        cmd.run(
            source_dir=params.get("source_dir"),
            platform=params["platform"],
            arch=params.get("arch", []),
            requirements=params.get("requirements", []),
            asset=params.get("asset"),
            exclude=params.get("exclude", []),
            skip_site_packages=params.get("skip_site_packages", False),
            compile_app=params.get("compile_app", False),
            compile_packages=params.get("compile_packages", False),
            cleanup=params.get("cleanup", False),
            cleanup_app=params.get("cleanup_app", False),
            cleanup_app_files=params.get("cleanup_app_files", []),
            cleanup_packages=params.get("cleanup_packages", False),
            cleanup_package_files=params.get("cleanup_package_files", []),
            verbose=params.get("verbose", False),
            pip_tool=params.get("pip_tool", "uv"),
        )
        return

    cmd = PackageCommand()
    cmd.run(
        source_dir=source_dir,
        platform=platform,
        arch=arch or [],
        requirements=requirements or [],
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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
