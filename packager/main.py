from typing import Annotated, List, Optional
import typer
from .package_command import PackageCommand

app = typer.Typer(
    name="python main.py",
    help="用于将 Python 应用打包以配合 serious_python 包的工具",
)


@app.command()
def package(
    platform: Annotated[
        str,
        typer.Option(
            "-p",
            "--platform",
            help="为特定平台安装依赖，例如 'Android'",
        ),
    ],
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
            help="输出资产路径，相对于 pubspec.yaml，用于将 Python 程序打包到其中",
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
) -> None:
    """将 Python 应用打包到 Flutter 资产中"""
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
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
