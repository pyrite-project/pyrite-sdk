import fnmatch
import hashlib
import json
import os
import platform as host_platform
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.rule import Rule

from .python_versions import PythonRelease, resolve_python_release
from .sitecustomize import sitecustomize_py
from .utils import macos_utils

mobile_pypi_url = "https://pypi.flet.dev"

default_site_packages_dir = "site-packages"
site_packages_env_var = "SERIOUS_PYTHON_SITE_PACKAGES"
legacy_site_packages_env_var = "serious_python_site_packages"
app_environment_var = "SERIOUS_PYTHON_APP"
flutter_packages_flutter_env_var = "SERIOUS_PYTHON_FLUTTER_PACKAGES"
allow_source_distros_env_var = "SERIOUS_PYTHON_ALLOW_SOURCE_DISTRIBUTIONS"
runtime_metadata_filename = ".pyrite-runtime.json"

platforms = {
    "Android": {
        "arm64-v8a": {"tag": "android-24-arm64_v8a", "mac_ver": ""},
        "armeabi-v7a": {"tag": "android-24-armeabi_v7a", "mac_ver": ""},
        "x86_64": {"tag": "android-24-x86_64", "mac_ver": ""},
    },
    "Darwin": {
        "arm64": {"tag": "", "mac_ver": "arm64"},
        "x86_64": {"tag": "", "mac_ver": "x86_64"},
    },
    "Windows": {
        "": {"tag": "", "mac_ver": ""},
    },
    "Linux": {
        "": {"tag": "", "mac_ver": ""},
    },
}

uv_python_platforms = {
    ("Android", "arm64-v8a"): "aarch64-linux-android",
    ("Android", "x86_64"): "x86_64-linux-android",
    ("Darwin", "arm64"): "aarch64-apple-darwin",
    ("Darwin", "x86_64"): "x86_64-apple-darwin",
    ("Windows", ""): "windows",
    ("Linux", ""): "linux",
}

junk_files_desktop = [
    "**.c",
    "**.h",
    "**.cpp",
    "**.hpp",
    "**.typed",
    "**.pyi",
    "**.pxd",
    "**.pyx",
    "**.a",
    "**.pdb",
    "__pycache__",
    "**/__pycache__",
]
junk_files_mobile = [
    *junk_files_desktop,
    "**.exe",
    "**.dll",
    "bin",
    "**/bin",
]


class PackageCommand:
    def __init__(self):
        self._verbose = False
        self._build_dir: Optional[Path] = None
        self._python_dir: Optional[Path] = None
        self._release: Optional[PythonRelease] = None
        self._console = Console()

    def _log(self, msg: str, style: str = "") -> None:
        if style:
            self._console.print(msg, style=style)
        else:
            self._console.print(msg)

    def _verbose_log(self, msg: str) -> None:
        if self._verbose:
            self._console.print(f"  [dim]{msg}[/dim]")

    def _header(self, title: str) -> None:
        self._console.print()
        self._console.print(Rule(style="dim"))
        self._console.print(f"  [bold]{title}[/bold]")
        self._console.print(Rule(style="dim"))

    @staticmethod
    def _archive_destination(
        destination: Path,
        architecture: str,
    ) -> Path:
        if not architecture:
            return destination
        return destination.with_name(
            f"{destination.stem}-{architecture}{destination.suffix}"
        )

    @classmethod
    def _archive_family(cls, destination: Path) -> set[Path]:
        architectures = {
            architecture
            for platform_architectures in platforms.values()
            for architecture in platform_architectures
            if architecture
        }
        return {
            destination,
            *(
                cls._archive_destination(destination, architecture)
                for architecture in architectures
            ),
        }

    @staticmethod
    def _flatten_architecture_package_dir(
        package_dir: Path,
        architecture: str,
    ) -> None:
        site_packages_dir = package_dir / default_site_packages_dir
        selected_architecture_dir = site_packages_dir / architecture
        if architecture and selected_architecture_dir.is_dir():
            shutil.copytree(
                selected_architecture_dir,
                site_packages_dir,
                dirs_exist_ok=True,
            )
        architectures = {
            known_architecture
            for platform_architectures in platforms.values()
            for known_architecture in platform_architectures
            if known_architecture
        }
        for known_architecture in architectures:
            architecture_dir = site_packages_dir / known_architecture
            if architecture_dir.is_dir():
                shutil.rmtree(architecture_dir)
            elif architecture_dir.exists():
                architecture_dir.unlink()

    @classmethod
    def _publish_archive_family(
        cls,
        destination: Path,
        staged_archives: list[tuple[Path, Path]],
    ) -> None:
        family_files = {
            candidate
            for archive in cls._archive_family(destination)
            for candidate in (archive, Path(f"{archive}.hash"))
        }
        for candidate in sorted(family_files, key=str):
            try:
                mode = candidate.lstat().st_mode
            except FileNotFoundError:
                continue
            if not stat.S_ISREG(mode):
                raise ValueError(
                    f"Archive output path is not a regular file: {candidate}"
                )
        backup_dir = Path(
            tempfile.mkdtemp(
                prefix="pyrite_plugin_archive_backup",
                dir=destination.parent,
            )
        )
        backups: dict[Path, Path] = {}
        cleanup_backup = True
        try:
            for candidate in sorted(family_files, key=str):
                if candidate.is_file():
                    backup = backup_dir / candidate.name
                    shutil.copy2(candidate, backup)
                    backups[candidate] = backup

            try:
                for staged_archive, archive_dest in staged_archives:
                    os.replace(staged_archive, archive_dest)
                    os.replace(
                        Path(f"{staged_archive}.hash"),
                        Path(f"{archive_dest}.hash"),
                    )
                produced_archives = {
                    archive_dest for _, archive_dest in staged_archives
                }
                for archive in (
                    cls._archive_family(destination) - produced_archives
                ):
                    archive.unlink(missing_ok=True)
                    Path(f"{archive}.hash").unlink(missing_ok=True)
            except Exception as publish_error:
                rollback_errors: list[Exception] = []
                for candidate in family_files:
                    try:
                        candidate.unlink(missing_ok=True)
                    except Exception as error:
                        rollback_errors.append(error)
                for candidate, backup in backups.items():
                    try:
                        shutil.copy2(backup, candidate)
                    except Exception as error:
                        rollback_errors.append(error)
                if rollback_errors:
                    cleanup_backup = False
                    raise RuntimeError(
                        "Archive publication failed and rollback was incomplete; "
                        f"backups remain in {backup_dir}"
                    ) from publish_error
                raise
        finally:
            if cleanup_backup:
                try:
                    shutil.rmtree(backup_dir)
                except Exception:
                    pass

    def _write_runtime_metadata(
        self,
        package_dir: Path,
        *,
        platform: str,
        architectures: list[str],
    ) -> None:
        if self._release is None:
            raise RuntimeError("Python runtime has not been selected")
        runtime_metadata = {
            "schema_version": 1,
            "runtime": {
                "implementation": "cpython",
                "python_version": self._release.short_version,
                "python_full_version": self._release.full_version,
            },
            "target": {
                "platform": platform,
                "architectures": [
                    architecture for architecture in architectures if architecture
                ],
            },
        }
        (package_dir / runtime_metadata_filename).write_text(
            json.dumps(runtime_metadata, indent=2) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _clear_package_directory(directory: Path) -> None:
        if not directory.exists():
            return
        for entry in directory.iterdir():
            if entry.name.startswith("."):
                continue
            if entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()

    def _install_arch_dependencies(
        self,
        *,
        platform: str,
        architecture: str,
        requirements: list[str],
        site_packages_dir: Path,
        pip_tool: str,
        is_mobile: bool,
        compile_packages: bool,
        cleanup: bool,
        cleanup_packages: bool,
        cleanup_package_files: list,
        junk_files: list[str],
        extra_pypi_indexes: list[str],
        flutter_packages_copied: bool,
    ) -> bool:
        target_config = platforms[platform][architecture]
        sitecustomize_dir: Optional[Path] = None
        try:
            sitecustomize_dir = Path(
                tempfile.mkdtemp(prefix="serious_python_sitecustomize")
            )
            sitecustomize_path = sitecustomize_dir / "sitecustomize.py"
            self._verbose_log(
                f"已在 {sitecustomize_path} 配置平台 "
                f"{platform}/{architecture} 的 sitecustomize.py"
            )
            sitecustomize_path.write_text(
                sitecustomize_py.replace(
                    "{platform}",
                    platform if target_config["tag"] else "",
                )
                .replace("{tag}", target_config["tag"])
                .replace("{mac_ver}", target_config["mac_ver"]),
                encoding="utf-8",
            )
            pip_env = {
                "PYTHONPATH": str(sitecustomize_dir),
                "PYTHONNOUSERSITE": "1",
                "PIP_REQUIRE_VIRTUALENV": "false",
            }

            site_packages_dir.mkdir(parents=True, exist_ok=True)
            pip_args: list[str] = []
            if is_mobile:
                pip_args.extend(["--only-binary", ":all:"])
                if allow_source_distros_env_var in os.environ:
                    pip_args.extend(
                        [
                            "--no-binary",
                            os.environ[allow_source_distros_env_var],
                        ]
                    )
            for index in extra_pypi_indexes:
                pip_args.extend(["--extra-index-url", index])

            if (
                pip_tool == "uv"
                and platform == "Android"
                and architecture == "armeabi-v7a"
            ):
                self._log(
                    "uv 不支持 Android armeabi-v7a，"
                    "改用目标 Python 的 pip"
                )
            install_cmd = self._build_install_command(
                pip_tool=pip_tool,
                pip_args=pip_args,
                site_packages_dir=str(site_packages_dir),
                requirements=requirements,
                platform=platform,
                arch=architecture,
            )
            print("运行安装依赖包命令:", " ".join(install_cmd))
            result = subprocess.run(
                install_cmd,
                env={**os.environ, **pip_env},
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if result.returncode != 0:
                self._console.print(f"[red]{result.stderr.decode()}[/red]")
                sys.exit(1)
            if self._verbose and result.stdout:
                self._verbose_log(result.stdout.decode())

            if flutter_packages_flutter_env_var in os.environ:
                flutter_packages_root_dir = Path(
                    os.environ[flutter_packages_flutter_env_var]
                )
                site_packages_flutter_dir = site_packages_dir / "flutter"
                if site_packages_flutter_dir.exists():
                    if not flutter_packages_copied:
                        self._verbose_log(
                            "正在将 Flutter 包复制到 "
                            f"{flutter_packages_root_dir}"
                        )
                        flutter_packages_root_dir.mkdir(
                            parents=True, exist_ok=True
                        )
                        self.copy_directory_with_progress(
                            site_packages_flutter_dir,
                            flutter_packages_root_dir,
                            str(site_packages_flutter_dir),
                            [],
                        )
                        flutter_packages_copied = True
                    shutil.rmtree(site_packages_flutter_dir)

            if compile_packages:
                with self._console.status(
                    "[bold green]"
                    f"正在编译应用包 {site_packages_dir}"
                    "[/bold green]"
                ) as _status:
                    subprocess.run(
                        [
                            str(self._target_python()),
                            "-m",
                            "compileall",
                            "-b",
                            str(site_packages_dir),
                        ],
                        check=True,
                    )
                self._verbose_log("删除原始 .py 文件")
                self.cleanup_dir(site_packages_dir, ["**.py"])

            if cleanup_packages or cleanup:
                all_junk_files = [*junk_files, *cleanup_package_files]
                if self._verbose:
                    self._verbose_log(
                        f"删除不必要的包文件和目录: {all_junk_files}"
                    )
                with self._console.status(
                    "[bold green]清理已安装的包..."
                ) as _status:
                    self.cleanup_dir(site_packages_dir, all_junk_files)
        finally:
            if sitecustomize_dir is not None and sitecustomize_dir.exists():
                self._verbose_log(
                    f"删除 sitecustomize 目录 {sitecustomize_dir}"
                )
                shutil.rmtree(sitecustomize_dir)

        return flutter_packages_copied

    def _create_archive(
        self,
        source: Path,
        destination: Path,
        *,
        reported_destination: Optional[Path] = None,
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
            self.calculate_file_hash(str(destination)),
            encoding="ascii",
        )

    def run(
        self,
        *,
        source_dir: Optional[str] = None,
        platform: str,
        arch: list,
        requirements: list,
        asset: Optional[str] = None,
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

        temp_dir: Optional[Path] = None
        self._build_dir = None
        self._python_dir = None
        self._release = None

        try:
            current_path = Path.cwd()
            asset_path = asset
            self._verbose = verbose

            source_path = Path(source_dir)
            if not source_path.is_absolute():
                source_path = current_path / source_path

            if platform not in platforms:
                self._console.print(f"[red]未知平台: {platform}[/red]")
                sys.exit(2)

            if not source_path.exists():
                self._console.print("[red]源目录不存在.[/red]")
                sys.exit(2)

            manifest_path = source_path / "plugin.toml"
            if not manifest_path.is_file():
                raise ValueError(f"plugin.toml 不存在: {manifest_path}")
            try:
                with manifest_path.open("rb") as file:
                    plugin_config = tomllib.load(file)
            except (OSError, tomllib.TOMLDecodeError) as exc:
                raise ValueError(f"无法读取 plugin.toml: {exc}") from exc
            plugin_general = plugin_config.get("general")
            if not isinstance(plugin_general, dict):
                raise ValueError("plugin.toml 缺少 [general]")
            manifest_python_version = plugin_general.get("python_version")
            if manifest_python_version is not None and (
                not isinstance(manifest_python_version, str)
                or not manifest_python_version
            ):
                raise ValueError(
                    "plugin.toml [general].python_version 必须是字符串"
                )
            self._release = resolve_python_release(manifest_python_version)
            self._log(
                f"目标 Python: [cyan]{self._release.short_version}[/cyan] "
                f"(CPython {self._release.full_version})"
            )

            selected_archs = [
                architecture
                for architecture in platforms[platform]
                if (not arch or architecture in arch)
                and (
                    platform != "Android"
                    or architecture in self._release.android_abis
                )
            ]
            if arch:
                unsupported = sorted(set(arch) - set(selected_archs))
                if unsupported:
                    raise ValueError(
                        "目标 Python 不发布这些架构: " + ", ".join(unsupported)
                    )

            is_mobile = platform == "Android"
            junk_files = junk_files_mobile if is_mobile else junk_files_desktop

            # Extra indexes
            extra_pypi_indexes = [mobile_pypi_url]
            self._verbose_log(f"额外的 PyPi 索引: {extra_pypi_indexes}")

            # ensure standard Dart/Flutter "build" directory exists
            self._build_dir = current_path / "build"
            if not self._build_dir.exists():
                self._build_dir.mkdir()

            # asset path
            app_staging_root = os.environ.get(app_environment_var)
            explicit_asset_requested = asset_path is not None and bool(
                asset_path.strip()
            )
            native_staging_mode = bool(
                app_staging_root and not explicit_asset_requested
            )
            if asset_path is None:
                plugin_id = plugin_general.get("id")
                if not isinstance(plugin_id, str) or not plugin_id:
                    raise ValueError("plugin.toml [general].id 必须是字符串")
                asset_path = f"build/{plugin_id}.zip"
            elif asset_path.startswith(("/", "\\")):
                asset_path = asset_path[1:]

            # create dest dir
            dest = current_path / asset_path
            dest_dir = dest.parent
            if not dest_dir.exists():
                self._log(f"新建资产目录: [yellow]{dest_dir}[/yellow]")
                dest_dir.mkdir(parents=True, exist_ok=True)

            # create temp dir
            temp_dir = Path(tempfile.mkdtemp(prefix="serious_python_temp"))
            self._verbose_log(f"临时目录: {temp_dir}")

            # ── Step: copy app ──
            self._header("复制应用代码")
            self._log(
                f"  来源: [green]{source_path}[/green]  →  [green]{temp_dir}[/green]"
            )
            copy_excludes = [s.strip() for s in exclude]
            excluded_roots: list[Path] = []
            if not native_staging_mode:
                resolved_source = source_path.resolve()
                for archive in self._archive_family(dest):
                    for candidate in (archive, Path(f"{archive}.hash")):
                        try:
                            relative_path = candidate.resolve().relative_to(
                                resolved_source
                            )
                        except ValueError:
                            continue
                        copy_excludes.append(str(relative_path))
                try:
                    self._build_dir.resolve().relative_to(resolved_source)
                except ValueError:
                    pass
                else:
                    excluded_roots.append(self._build_dir)
            self.copy_directory_with_progress(
                source_path,
                temp_dir,
                str(source_path),
                copy_excludes,
                excluded_roots,
            )
            self._log("  [green]OK: 复制完成[/green]")

            # ── Step: compile app ──
            if compile_app:
                self._header("编译 Python 源文件")
                with self._console.status(
                    "[bold green]正在编译 Python 源文件..."
                ) as _status:
                    subprocess.run(
                        [
                            str(self._target_python()),
                            "-m",
                            "compileall",
                            "-b",
                            str(temp_dir),
                        ],
                        check=True,
                    )
                self._verbose_log("正在删除原始 .py 文件...")
                self.cleanup_dir(temp_dir, ["**.py"])
                self._log("  [green]OK: 编译完成[/green]")

            # ── Step: cleanup app ──
            if cleanup_app or cleanup:
                app_junk_files = [*junk_files, *cleanup_app_files]
                if self._verbose:
                    self._verbose_log(
                        f"删除不必要的 app 文件和目录: {app_junk_files}"
                    )
                with self._console.status(
                    "[bold green]正在清理 app..."
                ) as _status:
                    self.cleanup_dir(temp_dir, app_junk_files)
                self._log("  [green]OK: 清理完成[/green]")

            # ── Step: install requirements ──
            if native_staging_mode and not skip_site_packages:
                self._header("安装依赖包")
                site_packages_root = os.environ.get(
                    site_packages_env_var
                ) or os.environ.get(legacy_site_packages_env_var)
                if not site_packages_root:
                    site_packages_root = self._build_dir / default_site_packages_dir
                site_packages_root = Path(site_packages_root)

                self._clear_package_directory(site_packages_root)

                flutter_packages_copied = False
                selected_archs_for_install = selected_archs if requirements else []
                # Progress bar for multi-arch install
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    TimeElapsedColumn(),
                    TimeRemainingColumn(),
                    console=self._console,
                ) as progress:
                    task = progress.add_task(
                        "安装依赖...", total=len(selected_archs_for_install)
                    )

                    for arch_key in selected_archs_for_install:
                        progress.update(
                            task,
                            description=f"处理架构 [cyan]{arch_key}[/cyan]...",
                        )
                        site_packages_dir = site_packages_root
                        if arch_key:
                            site_packages_dir = site_packages_root / arch_key
                        flutter_packages_copied = self._install_arch_dependencies(
                            platform=platform,
                            architecture=arch_key,
                            requirements=requirements,
                            site_packages_dir=site_packages_dir,
                            pip_tool=pip_tool,
                            is_mobile=is_mobile,
                            compile_packages=compile_packages,
                            cleanup=cleanup,
                            cleanup_packages=cleanup_packages,
                            cleanup_package_files=cleanup_package_files,
                            junk_files=junk_files,
                            extra_pypi_indexes=extra_pypi_indexes,
                            flutter_packages_copied=flutter_packages_copied,
                        )

                        progress.update(task, advance=1)

                if platform == "Darwin" and selected_archs_for_install:
                    macos_utils.merge_macos_site_packages(
                        str(site_packages_root / "arm64"),
                        str(site_packages_root / "x86_64"),
                        str(site_packages_root),
                        self._verbose,
                    )

                # synchronize pod
                sync_sh = site_packages_root / ".pod" / "sync_site_packages.sh"
                if sync_sh.exists():
                    self.run_exec("/bin/sh", [str(sync_sh)])

            if not (temp_dir / "plugin.toml").is_file():
                raise ValueError(
                    "打包产物缺少 plugin.toml；不能排除或清理该文件"
                )
            if not any(
                (temp_dir / entry_point).is_file()
                for entry_point in ("__main__.py", "__main__.pyc")
            ):
                raise ValueError(
                    "打包产物缺少 __main__.py 或 __main__.pyc；"
                    "不能排除或清理插件入口文件"
                )

            if native_staging_mode:
                self._write_runtime_metadata(
                    temp_dir,
                    platform=platform,
                    architectures=selected_archs,
                )
                staging_path = Path(app_staging_root)
                self._header("暂存应用目录")
                self._log(f"  输出: [green]{staging_path}[/green]")
                if staging_path.exists():
                    shutil.rmtree(staging_path)
                staging_path.mkdir(parents=True, exist_ok=True)
                self.copy_directory(temp_dir, staging_path, str(temp_dir), [])
            else:
                # ── Step: create archive ──
                self._header("创建应用存档")
                archive_destinations: list[Path] = []
                staged_archives: list[tuple[Path, Path]] = []
                flutter_packages_copied = False
                try:
                    for arch_key in selected_archs:
                        package_dir = Path(
                            tempfile.mkdtemp(prefix="pyrite_plugin_package")
                        )
                        try:
                            self.copy_directory(
                                temp_dir, package_dir, str(temp_dir), []
                            )
                            self._flatten_architecture_package_dir(
                                package_dir, arch_key
                            )
                            if requirements and not skip_site_packages:
                                self._clear_package_directory(
                                    package_dir / default_site_packages_dir
                                )
                                flutter_packages_copied = (
                                    self._install_arch_dependencies(
                                        platform=platform,
                                        architecture=arch_key,
                                        requirements=requirements,
                                        site_packages_dir=(
                                            package_dir
                                            / default_site_packages_dir
                                        ),
                                        pip_tool=pip_tool,
                                        is_mobile=is_mobile,
                                        compile_packages=compile_packages,
                                        cleanup=cleanup,
                                        cleanup_packages=cleanup_packages,
                                        cleanup_package_files=(
                                            cleanup_package_files
                                        ),
                                        junk_files=junk_files,
                                        extra_pypi_indexes=(
                                            extra_pypi_indexes
                                        ),
                                        flutter_packages_copied=(
                                            flutter_packages_copied
                                        ),
                                    )
                                )
                            self._write_runtime_metadata(
                                package_dir,
                                platform=platform,
                                architectures=[arch_key],
                            )
                            archive_dest = self._archive_destination(
                                dest, arch_key
                            )
                            archive_fd, archive_name = tempfile.mkstemp(
                                prefix="pyrite_plugin_archive",
                                suffix=".zip",
                                dir=dest_dir,
                            )
                            os.close(archive_fd)
                            staged_archive = Path(archive_name)
                            staged_archives.append(
                                (staged_archive, archive_dest)
                            )
                            self._create_archive(
                                package_dir,
                                staged_archive,
                                reported_destination=archive_dest,
                            )
                            archive_destinations.append(archive_dest)
                        finally:
                            if package_dir.exists():
                                shutil.rmtree(package_dir)
                    self._publish_archive_family(dest, staged_archives)
                finally:
                    for staged_archive, _ in staged_archives:
                        staged_archive.unlink(missing_ok=True)
                        Path(f"{staged_archive}.hash").unlink(
                            missing_ok=True
                        )

            # ── Done ──
            self._console.print()
            if native_staging_mode:
                self._console.print(
                    Panel.fit(
                        "[bold green]OK: 打包完成[/bold green]\n\n"
                        f"[white]目录:[/white]  [cyan]{app_staging_root}[/cyan]",
                        border_style="green",
                    )
                )
            else:
                archive_summary = "\n".join(
                    f"[white]存档:[/white]  [cyan]{archive}[/cyan]\n"
                    f"[white]哈希:[/white]  [cyan]{archive}.hash[/cyan]"
                    for archive in archive_destinations
                )
                self._console.print(
                    Panel.fit(
                        "[bold green]OK: 打包完成[/bold green]\n\n"
                        f"{archive_summary}",
                        border_style="green",
                    )
                )

        except Exception as e:
            self._console.print(f"\n[bold red]错误: {e}[/bold red]")
            raise
        finally:
            if temp_dir is not None and temp_dir.exists():
                self._verbose_log("删除临时目录...")
                shutil.rmtree(str(temp_dir))

    def _target_python(self) -> Path:
        """Return the cached standalone interpreter for the selected version."""
        if self._python_dir is not None:
            if host_platform.system() == "Windows":
                return self._python_dir / "python" / "python.exe"
            return self._python_dir / "python" / "bin" / "python3"
        if self._build_dir is None or self._release is None:
            raise RuntimeError("Python runtime has not been selected")

        system = host_platform.system()
        machine = host_platform.machine().lower()
        if system == "Windows":
            archive_arch = "x86_64-pc-windows-msvc"
        elif system == "Darwin":
            archive_arch = (
                "aarch64-apple-darwin"
                if machine in {"arm64", "aarch64"}
                else "x86_64-apple-darwin"
            )
        elif system == "Linux":
            archive_arch = (
                "aarch64-unknown-linux-gnu"
                if machine in {"arm64", "aarch64"}
                else "x86_64-unknown-linux-gnu"
            )
        else:
            raise RuntimeError(f"不支持的打包主机平台: {system}")

        release = self._release
        archive_name = (
            f"cpython-{release.full_version}+{release.standalone_release_date}"
            f"-{archive_arch}-install_only_stripped.tar.gz"
        )
        extract_name = (
            f"build_python_{release.full_version}-{release.standalone_release_date}"
        )
        python_dir = self._build_dir / extract_name
        marker = python_dir / ".python_build_id"
        build_id = f"{release.full_version}-{release.standalone_release_date}"

        if not (
            python_dir.exists() and marker.exists() and marker.read_text() == build_id
        ):
            cache_root = os.environ.get("FLET_CACHE_DIR")
            if cache_root:
                cache_base = Path(cache_root)
            else:
                home = os.environ.get("USERPROFILE") or os.environ.get(
                    "HOME", str(self._build_dir)
                )
                cache_base = Path(home) / ".flet" / "cache"
            cache_dir = (
                cache_base / "python-build-standalone" / release.standalone_release_date
            )
            cache_dir.mkdir(parents=True, exist_ok=True)
            archive_path = cache_dir / archive_name
            if not archive_path.exists():
                url = (
                    "https://github.com/astral-sh/python-build-standalone/"
                    f"releases/download/{release.standalone_release_date}/{archive_name}"
                )
                tmp_path = archive_path.with_suffix(archive_path.suffix + ".tmp")
                self._log(f"下载 Python runtime: [dim]{url}[/dim]")
                try:
                    with (
                        urllib.request.urlopen(url) as response,
                        tmp_path.open("wb") as output,
                    ):
                        if getattr(response, "status", 200) != 200:
                            raise RuntimeError(f"下载失败，HTTP {response.status}")
                        shutil.copyfileobj(response, output)
                    os.replace(tmp_path, archive_path)
                finally:
                    if tmp_path.exists():
                        tmp_path.unlink()

            staging_dir = python_dir.with_name(f"{python_dir.name}.tmp")
            if staging_dir.exists():
                shutil.rmtree(staging_dir)
            staging_dir.mkdir(parents=True)
            try:
                with tarfile.open(archive_path, "r:gz") as archive:
                    archive.extractall(staging_dir, filter="data")
                marker_path = staging_dir / ".python_build_id"
                marker_path.write_text(build_id, encoding="ascii")
                if python_dir.exists():
                    shutil.rmtree(python_dir)
                os.replace(staging_dir, python_dir)
            finally:
                if staging_dir.exists():
                    shutil.rmtree(staging_dir)

        self._python_dir = python_dir
        if host_platform.system() == "Windows":
            python_executable = python_dir / "python" / "python.exe"
        else:
            python_executable = python_dir / "python" / "bin" / "python3"
        if not python_executable.exists():
            raise RuntimeError(f"Python runtime 缺少解释器: {python_executable}")
        return python_executable

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
        target_python = str(self._target_python())
        if pip_tool == "pip" or (
            platform == "Android" and arch == "armeabi-v7a"
        ):
            return [
                target_python,
                "-m",
                "pip",
                "install",
                "--upgrade",
                "--disable-pip-version-check",
                *pip_args,
                "--target",
                site_packages_dir,
                *requirements,
            ]
        try:
            python_platform = uv_python_platforms[(platform, arch)]
        except KeyError as exc:
            raise ValueError(
                f"uv 不支持目标平台: {platform}/{arch or 'default'}"
            ) from exc
        return [
            "uv",
            "pip",
            "install",
            "--upgrade",
            "--no-progress",
            "--python",
            target_python,
            "--python-platform",
            python_platform,
            *pip_args,
            "--target",
            site_packages_dir,
            *requirements,
            "--index-strategy",
            "unsafe-best-match",
        ]

    def copy_directory_with_progress(
        self,
        source: Path,
        destination: Path,
        root_dir: str,
        exclude_list: list,
        excluded_roots: Optional[list[Path]] = None,
    ) -> None:
        """Copy files from source to destination with a progress bar."""
        resolved_excluded_roots = [
            excluded_root.resolve()
            for excluded_root in (excluded_roots or [])
        ]
        all_files = [
            f
            for f in source.rglob("*")
            if f.is_file()
            and str(f.relative_to(root_dir)) not in exclude_list
            and not any(
                f.resolve().is_relative_to(excluded_root)
                for excluded_root in resolved_excluded_roots
            )
        ]

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=self._console,
        ) as progress:
            task = progress.add_task("复制文件...", total=len(all_files))
            for f in all_files:
                rel = f.relative_to(source)
                dest_path = destination / rel
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(f), str(dest_path))
                progress.update(task, advance=1)

    def copy_directory(
        self,
        source: Path,
        destination: Path,
        root_dir: str,
        exclude_list: list,
    ) -> None:
        """Original recursive copy (kept for backward compatibility)."""
        for entity in source.iterdir():
            rel_path = str(Path(entity).relative_to(root_dir))
            if rel_path in exclude_list:
                continue
            if entity.is_dir():
                new_directory = destination / entity.name
                new_directory.mkdir(exist_ok=True)
                self.copy_directory(
                    entity.resolve(),
                    new_directory,
                    root_dir,
                    exclude_list,
                )
            elif entity.is_file():
                shutil.copy2(str(entity), str(destination / entity.name))

    def cleanup_dir(self, directory: Path, filesGlobs: list) -> None:
        self._verbose_log(f"清理目录 {directory}: {filesGlobs}")
        self.cleanup_dir_recursive(directory, filesGlobs)

    def cleanup_dir_recursive(self, directory: Path, globs: list) -> bool:
        empty_dir = True
        for entity in list(directory.iterdir()):
            if any(
                fnmatch.fnmatch(
                    str(entity).replace("\\", "/"), g.replace("\\", "/")
                )
                for g in globs
            ) and entity.exists():
                self._verbose_log(f"删除 {entity}")
                if entity.is_dir():
                    shutil.rmtree(str(entity))
                else:
                    entity.unlink()
            elif entity.is_dir():
                if self.cleanup_dir_recursive(entity, globs):
                    self._verbose_log(f"删除空目录 {entity}")
                    entity.rmdir()
                else:
                    empty_dir = False
            else:
                empty_dir = False
        return empty_dir

    def run_exec(
        self,
        execPath: str,
        args: list,
        environment: Optional[dict] = None,
    ) -> int:
        env = os.environ.copy()
        if environment:
            env.update({key: str(value) for key, value in environment.items()})

        proc = subprocess.Popen(
            [execPath, *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        assert proc.stdout is not None
        for line in proc.stdout:
            self._verbose_log(line.strip())

        _, stderr_text = proc.communicate()

        if proc.returncode != 0:
            self._console.print(f"[red]{stderr_text}[/red]")
            sys.exit(1)
        return proc.returncode

    def zip_directory_posix(
        self,
        source: Path,
        dest: Path,
        progress: Optional[Progress] = None,
        task_id: Optional[TaskID] = None,
    ) -> None:
        all_files = [f for f in source.rglob("*") if f.is_file()]

        if progress and task_id is not None:
            progress.update(task_id, total=len(all_files))

        with zipfile.ZipFile(str(dest), "w", zipfile.ZIP_DEFLATED) as zf:
            for entity in all_files:
                relative_path = entity.relative_to(source)
                posix_path = "/".join(relative_path.parts)
                zf.write(str(entity), posix_path)
                if progress and task_id is not None:
                    progress.update(task_id, advance=1)

    def calculate_file_hash(self, path: str) -> str:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
