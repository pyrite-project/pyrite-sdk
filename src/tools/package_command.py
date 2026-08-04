from __future__ import annotations

import os
import platform as host_platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from pyrite_sdk.models.manifest import (
    ManifestValidationError,
    PluginManifestV2,
    load_file,
)
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.rule import Rule

from .package_artifacts import (
    archive_destination,
    archive_family,
    archive_outputs,
    build_archives,
    calculate_file_hash,
    cleanup_directory,
    clear_package_directory,
    copy_directory,
    copy_directory_with_progress,
    flatten_architecture_package_dir,
    publish_archive_family,
    resolve_target_python,
    run_exec,
    write_runtime_metadata,
    zip_directory_posix,
)
from .package_installer import (
    allow_source_distros_env_var,
    app_environment_var,
    build_install_command,
    default_site_packages_dir,
    flutter_packages_flutter_env_var,
    install_arch_dependencies,
    install_native_dependencies,
    junk_files_desktop,
    junk_files_mobile,
    legacy_site_packages_env_var,
    mobile_pypi_url,
    platforms,
    runtime_metadata_filename,
    select_architectures,
    site_packages_env_var,
    uv_python_platforms,
)
from .python_versions import PythonRelease, resolve_python_release
from .utils import macos_utils

__all__ = [
    "PackageCommand",
    "allow_source_distros_env_var",
    "app_environment_var",
    "default_site_packages_dir",
    "flutter_packages_flutter_env_var",
    "legacy_site_packages_env_var",
    "macos_utils",
    "mobile_pypi_url",
    "platforms",
    "runtime_metadata_filename",
    "site_packages_env_var",
    "uv_python_platforms",
]


class PackageCommand:
    _archive_destination = staticmethod(archive_destination)
    _archive_family = staticmethod(archive_family)
    _flatten_architecture_package_dir = staticmethod(flatten_architecture_package_dir)
    _publish_archive_family = staticmethod(publish_archive_family)
    _clear_package_directory = staticmethod(clear_package_directory)
    _install_arch_dependencies = install_arch_dependencies
    copy_directory = staticmethod(copy_directory)
    zip_directory_posix = staticmethod(zip_directory_posix)
    calculate_file_hash = staticmethod(calculate_file_hash)

    def __init__(self) -> None:
        self._verbose = False
        self._build_dir: Path | None = None
        self._python_dir: Path | None = None
        self._release: PythonRelease | None = None
        self._console = Console()

    def _log(self, message: str, style: str = "") -> None:
        if style:
            self._console.print(message, style=style)
        else:
            self._console.print(message)

    def _verbose_log(self, message: str) -> None:
        if self._verbose:
            self._console.print(f"  [dim]{message}[/dim]")

    def _header(self, title: str) -> None:
        self._console.print()
        self._console.print(Rule(style="dim"))
        self._console.print(f"  [bold]{title}[/bold]")
        self._console.print(Rule(style="dim"))

    @staticmethod
    def _read_manifest(manifest: Path) -> PluginManifestV2:
        try:
            return load_file(manifest)
        except ManifestValidationError as exc:
            raise ValueError(f"{exc.code}: {exc.message}") from exc

    def _copy_app(
        self,
        source: Path,
        destination: Path,
        archive: Path,
        exclude: list,
        native_staging: bool,
    ) -> None:
        self._header("复制应用代码")
        self._log(f"  来源: [green]{source}[/green]  → [green]{destination}[/green]")
        copy_excludes = [value.strip() for value in exclude]
        excluded_roots: list[Path] = []
        if not native_staging:
            resolved_source = source.resolve()
            output_parent: Path | None = None
            try:
                output_parent = archive.parent.resolve().relative_to(resolved_source)
            except ValueError:
                pass
            for output in archive_outputs(archive):
                for candidate in (output, Path(f"{output}.hash")):
                    try:
                        relative = candidate.resolve().relative_to(resolved_source)
                    except ValueError:
                        continue
                    copy_excludes.append(str(relative))
            if output_parent is not None:
                for existing_output in archive.parent.glob(
                    f"{archive.stem}-*{archive.suffix}*"
                ):
                    copy_excludes.append(
                        str(existing_output.resolve().relative_to(resolved_source))
                    )
            if self._build_dir is not None:
                try:
                    self._build_dir.resolve().relative_to(resolved_source)
                except ValueError:
                    pass
                else:
                    excluded_roots.append(self._build_dir)
        self.copy_directory_with_progress(
            source,
            destination,
            str(source),
            copy_excludes,
            excluded_roots,
        )
        self._log("  [green]OK: 复制完成[/green]")

    def _process_app(
        self,
        app_dir: Path,
        *,
        compile_app: bool,
        cleanup_app: bool,
        cleanup_globs: list,
    ) -> None:
        if compile_app:
            self._header("编译 Python 源文件")
            with self._console.status("[bold green]正在编译 Python 源文件..."):
                subprocess.run(
                    [
                        str(self._target_python()),
                        "-m",
                        "compileall",
                        "-b",
                        str(app_dir),
                    ],
                    check=True,
                )
            self._verbose_log("正在删除原始 .py 文件...")
            self.cleanup_dir(app_dir, ["**.py"])
            self._log("  [green]OK: 编译完成[/green]")
        if cleanup_app:
            self._verbose_log(f"删除不必要的 app 文件和目录: {cleanup_globs}")
            with self._console.status("[bold green]正在清理 app..."):
                self.cleanup_dir(app_dir, cleanup_globs)
            self._log("  [green]OK: 清理完成[/green]")

    @staticmethod
    def _validate_staged_app(app_dir: Path) -> None:
        if not (app_dir / "plugin.toml").is_file():
            raise ValueError("打包产物缺少 plugin.toml；不能排除或清理该文件")
        if not any(
            (app_dir / entry_point).is_file()
            for entry_point in ("__main__.py", "__main__.pyc")
        ):
            raise ValueError(
                "打包产物缺少 __main__.py 或 __main__.pyc；不能排除或清理插件入口文件"
            )

    def run(
        self,
        *,
        source_dir: str | None = None,
        platform: str,
        arch: list,
        requirements: list,
        asset: str | None = None,
        exclude: list,
        skip_site_packages: bool = False,
        compile_app: bool = False,
        compile_packages: bool = False,
        cleanup: bool = False,
        cleanup_app: bool = False,
        cleanup_app_files: list,
        cleanup_packages: bool = False,
        cleanup_package_files: list,
        verbose: bool = False,
        pip_tool: str = "uv",
    ) -> None:
        self._console.print(
            Panel.fit(
                "[bold cyan]Pyrite SDK Packager[/bold cyan]",
                border_style="cyan",
            )
        )
        if source_dir is None:
            self._console.print("[red]错误: 未提供源目录[/red]")
            sys.exit(1)

        temp_dir: Path | None = None
        self._build_dir = None
        self._python_dir = None
        self._release = None
        try:
            current_path = Path.cwd()
            self._verbose = verbose
            source = Path(source_dir)
            if not source.is_absolute():
                source = current_path / source
            if platform not in platforms:
                self._console.print(f"[red]未知平台: {platform}[/red]")
                sys.exit(2)
            if not source.exists():
                self._console.print("[red]源目录不存在.[/red]")
                sys.exit(2)

            manifest = self._read_manifest(source / "plugin.toml")
            requested_version = manifest.python_version
            self._release = resolve_python_release(requested_version)
            self._log(
                f"目标 Python: [cyan]{self._release.short_version}[/cyan] "
                f"(CPython {self._release.full_version})"
            )
            selected_architectures = select_architectures(platform, arch, self._release)
            junk_files = (
                junk_files_mobile if platform == "Android" else junk_files_desktop
            )
            self._verbose_log(f"额外的 PyPi 索引: {[mobile_pypi_url]}")

            self._build_dir = current_path / "build"
            if not self._build_dir.exists():
                self._build_dir.mkdir()

            app_staging_root = os.environ.get(app_environment_var)
            explicit_asset = asset is not None and bool(asset.strip())
            native_staging = bool(app_staging_root and not explicit_asset)
            plugin_id = manifest.id
            asset_path = asset if explicit_asset else None
            if asset_path is None:
                asset_path = f"build/{plugin_id}.zip"
            elif asset_path.startswith(("/", "\\")):
                asset_path = asset_path[1:]
            requested_archive = current_path / asset_path
            archive = requested_archive.with_name(
                f"{plugin_id}{requested_archive.suffix}"
            )
            if not archive.parent.exists():
                self._log(f"新建资产目录: [yellow]{archive.parent}[/yellow]")
                archive.parent.mkdir(parents=True, exist_ok=True)

            temp_dir = Path(tempfile.mkdtemp(prefix="serious_python_temp"))
            self._verbose_log(f"临时目录: {temp_dir}")
            self._copy_app(source, temp_dir, archive, exclude, native_staging)
            app_cleanup_globs = [*junk_files, *cleanup_app_files]
            self._process_app(
                temp_dir,
                compile_app=compile_app,
                cleanup_app=cleanup_app or cleanup,
                cleanup_globs=app_cleanup_globs,
            )
            package_cleanup_globs = (
                [*junk_files, *cleanup_package_files]
                if cleanup_packages or cleanup
                else []
            )
            if native_staging and not skip_site_packages:
                install_native_dependencies(
                    self,
                    platform=platform,
                    architectures=selected_architectures,
                    requirements=requirements,
                    build_dir=self._build_dir,
                    pip_tool=pip_tool,
                    compile_packages=compile_packages,
                    cleanup_globs=package_cleanup_globs,
                )

            self._validate_staged_app(temp_dir)
            if native_staging:
                self._write_runtime_metadata(
                    temp_dir,
                    platform=platform,
                    architectures=selected_architectures,
                )
                staging_path = Path(app_staging_root)
                self._header("暂存应用目录")
                self._log(f"  输出: [green]{staging_path}[/green]")
                if staging_path.exists():
                    shutil.rmtree(staging_path)
                staging_path.mkdir(parents=True, exist_ok=True)
                self.copy_directory(temp_dir, staging_path, str(temp_dir), [])
                archives: list[Path] = []
            else:
                archives = build_archives(
                    self,
                    app_dir=temp_dir,
                    destination=archive,
                    platform=platform,
                    architectures=selected_architectures,
                    requirements=requirements,
                    skip_site_packages=skip_site_packages,
                    pip_tool=pip_tool,
                    compile_packages=compile_packages,
                    cleanup_globs=package_cleanup_globs,
                )

            self._console.print()
            if native_staging:
                summary = (
                    "[bold green]OK: 打包完成[/bold green]\n\n"
                    f"[white]目录:[/white]  [cyan]{app_staging_root}[/cyan]"
                )
            else:
                archive_summary = "\n".join(
                    f"[white]存档:[/white]  [cyan]{output}[/cyan]\n"
                    f"[white]哈希:[/white]  [cyan]{output}.hash[/cyan]"
                    for output in archives
                )
                summary = f"[bold green]OK: 打包完成[/bold green]\n\n{archive_summary}"
            self._console.print(Panel.fit(summary, border_style="green"))
        except Exception as error:
            self._console.print(f"\n[bold red]错误: {error}[/bold red]")
            raise
        finally:
            if temp_dir is not None and temp_dir.exists():
                self._verbose_log("删除临时目录...")
                shutil.rmtree(temp_dir)

    def _write_runtime_metadata(
        self,
        package_dir: Path,
        *,
        platform: str,
        architectures: list[str],
    ) -> None:
        if self._release is None:
            raise RuntimeError("Python runtime has not been selected")
        write_runtime_metadata(
            package_dir,
            self._release,
            platform=platform,
            architectures=architectures,
        )

    def _create_archive(
        self,
        source: Path,
        destination: Path,
        *,
        reported_destination: Path | None = None,
    ) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        output_path = reported_destination or destination
        self._log(f"  输出: [green]{output_path}[/green]")
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=self._console,
        ) as progress:
            task = progress.add_task("打包中...", total=0)
            self.zip_directory_posix(source, destination, progress, task)
        self._log("  [green]OK: 存档创建完成[/green]")
        self._log(f"  哈希: [green]{output_path}.hash[/green]")
        Path(f"{destination}.hash").write_text(
            self.calculate_file_hash(str(destination)), encoding="ascii"
        )

    def _target_python(self) -> Path:
        if self._python_dir is not None:
            if host_platform.system() == "Windows":
                return self._python_dir / "python" / "python.exe"
            return self._python_dir / "python" / "bin" / "python3"
        if self._build_dir is None or self._release is None:
            raise RuntimeError("Python runtime has not been selected")
        executable, self._python_dir = resolve_target_python(
            self._build_dir, self._release, self._log
        )
        return executable

    def _build_install_command(
        self,
        *,
        pip_tool: str,
        pip_args: list[str],
        site_packages_dir: str,
        requirements: list[str],
        platform: str,
        arch: str,
    ) -> list[str]:
        return build_install_command(
            pip_tool=pip_tool,
            pip_args=pip_args,
            target_python=str(self._target_python()),
            site_packages_dir=site_packages_dir,
            requirements=requirements,
            platform=platform,
            architecture=arch,
        )

    def copy_directory_with_progress(
        self,
        source: Path,
        destination: Path,
        root_dir: str,
        exclude_list: list,
        excluded_roots: list[Path] | None = None,
    ) -> None:
        copy_directory_with_progress(
            source,
            destination,
            root_dir,
            exclude_list,
            self._console,
            excluded_roots,
        )

    def cleanup_dir(self, directory: Path, filesGlobs: list) -> None:
        self._verbose_log(f"清理目录 {directory}: {filesGlobs}")
        self.cleanup_dir_recursive(directory, filesGlobs)

    def cleanup_dir_recursive(self, directory: Path, globs: list) -> bool:
        return cleanup_directory(directory, globs, self._verbose_log)

    def run_exec(
        self,
        execPath: str,
        args: list,
        environment: dict | None = None,
    ) -> int:
        return run_exec(
            execPath,
            args,
            self._console,
            self._verbose_log,
            environment,
        )
