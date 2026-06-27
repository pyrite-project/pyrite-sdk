import fnmatch
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

from rich.console import Console
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
from rich.panel import Panel
from rich.rule import Rule

from .utils import macos_utils
from .sitecustomize import sitecustomize_py

mobile_pypi_url = "https://pypi.flet.dev"

default_site_packages_dir = "site-packages"
site_packages_env_var = "serious_python_site_packages"
flutter_packages_flutter_env_var = "SERIOUS_PYTHON_FLUTTER_PACKAGES"
allow_source_distros_env_var = "SERIOUS_PYTHON_ALLOW_SOURCE_DISTRIBUTIONS"

platforms = {
    "Android": {
        "arm64-v8a": {"tag": "android-24-arm64-v8a", "mac_ver": ""},
        "armeabi-v7a": {"tag": "android-24-armeabi-v7a", "mac_ver": ""},
        "x86_64": {"tag": "android-24-x86_64", "mac_ver": ""},
        "x86": {"tag": "android-24-x86", "mac_ver": ""},
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

        try:
            current_path = Path.cwd()

            # args
            source_dir_path: Optional[str] = source_dir
            arch_arg: list = arch
            asset_path: Optional[str] = asset
            skip_site_packages: bool = skip_site_packages
            compile_app: bool = compile_app
            compile_packages: bool = compile_packages
            cleanup_app: bool = cleanup_app
            cleanup_app_files: list = cleanup_app_files
            cleanup_packages: bool = cleanup_packages
            cleanup_package_files: list = cleanup_package_files
            self._verbose = verbose

            if not Path(source_dir_path).is_absolute():
                source_dir_path = str(current_path / source_dir_path)

            source_path = Path(source_dir_path)

            if platform not in platforms:
                self._console.print(f"[red]未知平台: {platform}[/red]")
                sys.exit(2)

            if not source_path.exists():
                self._console.print("[red]源目录不存在.[/red]")
                sys.exit(2)

            is_mobile = platform in ("iOS", "Android")

            junk_files = junk_files_mobile if is_mobile else junk_files_desktop

            # Extra indexes
            extra_pypi_indexes = [mobile_pypi_url]
            self._verbose_log(f"额外的 PyPi 索引: {extra_pypi_indexes}")

            # ensure standard Dart/Flutter "build" directory exists
            self._build_dir = current_path / "build"
            if not self._build_dir.exists():
                self._build_dir.mkdir()

            # asset path
            if asset_path is None:
                asset_path = "build/app.zip"
            elif asset_path.startswith("/") or asset_path.startswith("\\"):
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
            self.copy_directory_with_progress(
                source_path, temp_dir, str(source_path),
                [s.strip() for s in exclude],
            )
            self._log("  [green]✔ 复制完成[/green]")

            # ── Step: compile app ──
            if compile_app:
                self._header("编译 Python 源文件")
                with self._console.status(
                    "[bold green]正在编译 Python 源文件..."
                ) as _status:
                    subprocess.run(
                        [sys.executable, "-m", "compileall", "-b", str(temp_dir)]
                    )
                self._verbose_log("正在删除原始 .py 文件...")
                self.cleanup_dir(temp_dir, ["**.py"])
                self._log("  [green]✔ 编译完成[/green]")

            # ── Step: cleanup app ──
            if cleanup_app or cleanup:
                al_junk_files = [*junk_files, *cleanup_app_files]
                if self._verbose:
                    self._verbose_log(
                        f"删除不必要的 app 文件和目录: {al_junk_files}"
                    )
                with self._console.status(
                    "[bold green]正在清理 app..."
                ) as _status:
                    self.cleanup_dir(temp_dir, al_junk_files)
                self._log("  [green]✔ 清理完成[/green]")

            # ── Step: install requirements ──
            if requirements and not skip_site_packages:
                self._header("安装依赖包")
                site_packages_root = None

                if site_packages_env_var in os.environ:
                    site_packages_root = os.environ[site_packages_env_var]
                if site_packages_root is None or site_packages_root == "":
                    site_packages_root = str(temp_dir / "site-packages")

                if Path(site_packages_root).exists():
                    for f in Path(site_packages_root).iterdir():
                        if not f.name.startswith("."):
                            shutil.rmtree(str(f))

                flutter_packages_copied = False
                selected_archs = [
                    a for a in platforms[platform]
                    if not arch_arg or a in arch_arg
                ]

                # Progress bar for multi-arch install
                progress = Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    TimeElapsedColumn(),
                    TimeRemainingColumn(),
                    console=self._console,
                )

                with progress:
                    task = progress.add_task(
                        "安装依赖...", total=len(selected_archs)
                    )

                    for arch_key in selected_archs:
                        arch_value = platforms[platform][arch_key]
                        progress.update(
                            task,
                            description=f"处理架构 [cyan]{arch_key}[/cyan]...",
                        )

                        site_packages_dir = None
                        pip_env = None
                        sitecustomize_dir: Optional[Path] = None

                        try:
                            # customized pip
                            sitecustomize_dir = Path(
                                tempfile.mkdtemp(
                                    prefix="serious_python_sitecustomize"
                                )
                            )
                            if not sitecustomize_dir.exists():
                                sitecustomize_dir.mkdir(
                                    parents=True, exist_ok=True
                                )
                            sitecustomize_path = (
                                sitecustomize_dir / "sitecustomize.py"
                            )
                            self._verbose_log(
                                f"已在 {sitecustomize_path} 配置平台 "
                                f"{platform}/{arch_key} 的 sitecustomize.py"
                            )

                            sitecustomize_path.write_text(
                                sitecustomize_py.replace(
                                    "{platform}",
                                    platform if arch_value["tag"] else "",
                                )
                                .replace("{tag}", arch_value["tag"])
                                .replace("{mac_ver}", arch_value["mac_ver"])
                            )

                            pip_env = {
                                "PYTHONPATH": sitecustomize_dir,
                                "PYTHONNOUSERSITE": "1",
                            }

                            if arch_key:
                                site_packages_dir = str(
                                    Path(site_packages_root) / arch_key
                                )
                            else:
                                site_packages_dir = site_packages_root
                            if not Path(site_packages_dir).exists():
                                Path(site_packages_dir).mkdir(
                                    parents=True, exist_ok=True
                                )

                            pip_args = []

                            if is_mobile:
                                pip_args.extend(["--only-binary", ":all:"])
                                if allow_source_distros_env_var in os.environ:
                                    pip_args.extend(
                                        [
                                            "--no-binary",
                                            os.environ[
                                                allow_source_distros_env_var
                                            ],
                                        ]
                                    )

                            for index in extra_pypi_indexes:
                                pip_args.extend(["--extra-index-url", index])

                            if pip_tool == "pip":
                                install_cmd = [
                                    sys.executable, "-m", "pip", "install",
                                    "--upgrade",
                                    *pip_args,
                                    "--target",
                                    site_packages_dir,
                                    *requirements,
                                ]
                            else:
                                install_cmd = [
                                    "uv",
                                    "pip",
                                    "install",
                                    "--upgrade",
                                    "--no-progress",
                                    *pip_args,
                                    "--target",
                                    site_packages_dir,
                                    *requirements,
                                    "--index-strategy",
                                    "unsafe-best-match",
                                ]

                            result = subprocess.run(
                                install_cmd,
                                env={
                                    **os.environ,
                                    **{
                                        k: str(v)
                                        for k, v in pip_env.items()
                                    },
                                }
                                if pip_env
                                else None,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                            )
                            if result.returncode != 0:
                                self._console.print(
                                    f"[red]{result.stderr.decode()}[/red]"
                                )
                                sys.exit(1)
                            if self._verbose and result.stdout:
                                self._verbose_log(result.stdout.decode())

                            # move $site_packages_dir/flutter if env var is defined
                            if flutter_packages_flutter_env_var in os.environ:
                                flutter_packages_root = os.environ[
                                    flutter_packages_flutter_env_var
                                ]
                                flutter_packages_root_dir = Path(
                                    flutter_packages_root
                                )
                                site_packages_flutter_dir = (
                                    Path(site_packages_dir) / "flutter"
                                )
                                if site_packages_flutter_dir.exists():
                                    if not flutter_packages_copied:
                                        self._verbose_log(
                                            f"正在将 Flutter 包复制到 "
                                            f"{flutter_packages_root}"
                                        )
                                        if (
                                            not flutter_packages_root_dir.exists()
                                        ):
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
                                    shutil.rmtree(
                                        str(site_packages_flutter_dir)
                                    )

                            # compile packages
                            if compile_packages:
                                with self._console.status(
                                    "[bold green]"
                                    f"正在编译应用包 {site_packages_dir}"
                                    "[/bold green]"
                                ) as _status:
                                    subprocess.run(
                                        [
                                            sys.executable,
                                            "-m",
                                            "compileall",
                                            "-b",
                                            site_packages_dir,
                                        ]
                                    )
                                self._verbose_log("删除原始 .py 文件")
                                self.cleanup_dir(
                                    Path(site_packages_dir), ["**.py"]
                                )

                            # cleanup packages
                            if cleanup_packages or cleanup:
                                al_junk_files = [
                                    *junk_files,
                                    *cleanup_package_files,
                                ]
                                if self._verbose:
                                    self._verbose_log(
                                        "删除不必要的包文件和目录: "
                                        f"{al_junk_files}"
                                    )
                                with self._console.status(
                                    "[bold green]清理已安装的包..."
                                ) as _status:
                                    self.cleanup_dir(
                                        Path(site_packages_dir), al_junk_files
                                    )

                        finally:
                            if (
                                sitecustomize_dir is not None
                                and sitecustomize_dir.exists()
                            ):
                                self._verbose_log(
                                    f"删除 sitecustomize 目录 {sitecustomize_dir}"
                                )
                                shutil.rmtree(str(sitecustomize_dir))

                        progress.update(task, advance=1)

                if platform == "Darwin":
                    macos_utils.merge_macos_site_packages(
                        str(Path(site_packages_root) / "arm64"),
                        str(Path(site_packages_root) / "x86_64"),
                        str(Path(site_packages_root)),
                        self._verbose,
                    )

                # synchronize pod
                sync_sh = (
                    Path(site_packages_root) / ".pod" / "sync_site_packages.sh"
                )
                if sync_sh.exists():
                    self.run_exec("/bin/sh", [str(sync_sh)])

            # ── Step: create archive ──
            self._header("创建应用存档")
            self._log(
                f"  输出: [green]{dest}[/green]"
            )
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=self._console,
            ) as progress:
                task = progress.add_task("打包中...", total=0)
                self.zip_directory_posix(temp_dir, dest, progress, task)
            self._log("  [green]✔ 存档创建完成[/green]")

            # ── Step: hash ──
            self._log(
                f"  哈希: [green]{dest}.hash[/green]"
            )
            Path(f"{dest}.hash").write_text(
                self.calculate_file_hash(str(dest))
            )

            # ── Done ──
            self._console.print()
            self._console.print(
                Panel.fit(
                    "[bold green]✔ 打包完成[/bold green]\n\n"
                    f"[white]存档:[/white]  [cyan]{dest}[/cyan]\n"
                    f"[white]哈希:[/white]  [cyan]{dest}.hash[/cyan]",
                    border_style="green",
                )
            )

        except Exception as e:
            self._console.print(f"\n[bold red]错误: {e}[/bold red]")
        finally:
            if temp_dir is not None and temp_dir.exists():
                self._verbose_log("删除临时目录...")
                shutil.rmtree(str(temp_dir))

    def copy_directory_with_progress(
        self,
        source: Path,
        destination: Path,
        root_dir: str,
        exclude_list: list,
    ) -> None:
        """Copy files from source to destination with a progress bar."""
        all_files = [
            f
            for f in source.rglob("*")
            if f.is_file() and str(f.relative_to(root_dir)) not in exclude_list
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
        emptyDir = True
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
                    emptyDir = False
            else:
                emptyDir = False
        return emptyDir

    def run_exec(
        self,
        execPath: str,
        args: list,
        environment: Optional[dict] = None,
    ) -> int:
        env = os.environ.copy()
        if environment:
            for k, v in environment.items():
                if isinstance(v, Path):
                    env[k] = str(v)
                else:
                    env[k] = str(v)
            if "PYTHONPATH" in environment:
                env["PYTHONPATH"] = str(environment["PYTHONPATH"])

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

        stdout, stderr_text = proc.communicate()

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
                relativePath = entity.relative_to(source)
                posixPath = "/".join(relativePath.parts)
                zf.write(str(entity), posixPath)
                if progress and task_id is not None:
                    progress.update(task_id, advance=1)

    def calculate_file_hash(self, path: str) -> str:
        digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        return digest
