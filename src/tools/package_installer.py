from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from .python_versions import PythonRelease
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

platforms = {
    "Android": {
        "arm64-v8a": {
            "tag": "android-24-arm64_v8a",
            "mac_ver": "",
        },
        "armeabi-v7a": {
            "tag": "android-24-armeabi_v7a",
            "mac_ver": "",
        },
        "x86_64": {
            "tag": "android-24-x86_64",
            "mac_ver": "",
        },
    },
    "Darwin": {
        "arm64": {
            "tag": "",
            "mac_ver": "arm64",
        },
        "x86_64": {
            "tag": "",
            "mac_ver": "x86_64",
        },
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
_pip_only_targets = {("Android", "armeabi-v7a")}
architectures = frozenset(
    architecture
    for platform_targets in platforms.values()
    for architecture in platform_targets
    if architecture
)


def select_architectures(
    platform: str,
    requested: list[str],
    release: PythonRelease,
) -> list[str]:
    selected = [
        architecture
        for architecture in platforms[platform]
        if (not requested or architecture in requested)
        and (platform != "Android" or architecture in release.android_abis)
    ]
    if requested:
        unsupported = sorted(set(requested) - set(selected))
        if unsupported:
            raise ValueError("目标 Python 不发布这些架构: " + ", ".join(unsupported))
    return selected


def build_install_command(
    *,
    pip_tool: str,
    pip_args: list[str],
    target_python: str,
    site_packages_dir: str,
    requirements: list[str],
    platform: str,
    architecture: str,
) -> list[str]:
    if pip_tool == "pip" or (platform, architecture) in _pip_only_targets:
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
        python_platform = uv_python_platforms[(platform, architecture)]
    except KeyError as exc:
        raise ValueError(
            f"uv 不支持目标平台: {platform}/{architecture or 'default'}"
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


def install_arch_dependencies(
    command,
    *,
    platform: str,
    architecture: str,
    requirements: list[str],
    site_packages_dir: Path,
    pip_tool: str,
    compile_packages: bool,
    cleanup_globs: list[str],
    flutter_packages_copied: bool,
) -> bool:
    config = platforms[platform][architecture]
    with tempfile.TemporaryDirectory(
        prefix="serious_python_sitecustomize"
    ) as temporary_dir:
        try:
            sitecustomize_path = Path(temporary_dir) / "sitecustomize.py"
            command._verbose_log(
                f"已在 {sitecustomize_path} 配置平台 "
                f"{platform}/{architecture} 的 sitecustomize.py"
            )
            sitecustomize_path.write_text(
                sitecustomize_py.replace(
                    "{platform}", platform if config["tag"] else ""
                )
                .replace("{tag}", config["tag"])
                .replace("{mac_ver}", config["mac_ver"]),
                encoding="utf-8",
            )
            pip_args: list[str] = []
            if platform == "Android":
                pip_args.extend(["--only-binary", ":all:"])
                if allow_source_distros_env_var in os.environ:
                    pip_args.extend(
                        ["--no-binary", os.environ[allow_source_distros_env_var]]
                    )
            pip_args.extend(["--extra-index-url", mobile_pypi_url])
            if pip_tool == "uv" and (platform, architecture) in _pip_only_targets:
                command._log("uv 不支持 Android armeabi-v7a，改用目标 Python 的 pip")
            install_command = command._build_install_command(
                pip_tool=pip_tool,
                pip_args=pip_args,
                site_packages_dir=str(site_packages_dir),
                requirements=requirements,
                platform=platform,
                arch=architecture,
            )
            print("运行安装依赖包命令:", " ".join(install_command))
            result = subprocess.run(
                install_command,
                env={
                    **os.environ,
                    "PYTHONPATH": temporary_dir,
                    "PYTHONNOUSERSITE": "1",
                    "PIP_REQUIRE_VIRTUALENV": "false",
                },
                capture_output=True,
                check=False,
            )
            if result.returncode != 0:
                command._console.print(f"[red]{result.stderr.decode()}[/red]")
                sys.exit(1)
            if result.stdout:
                command._verbose_log(result.stdout.decode())

            flutter_dir = site_packages_dir / "flutter"
            if flutter_packages_flutter_env_var in os.environ and flutter_dir.exists():
                flutter_root = Path(os.environ[flutter_packages_flutter_env_var])
                if not flutter_packages_copied:
                    command._verbose_log(f"正在将 Flutter 包复制到 {flutter_root}")
                    flutter_root.mkdir(parents=True, exist_ok=True)
                    command.copy_directory_with_progress(
                        flutter_dir,
                        flutter_root,
                        str(flutter_dir),
                        [],
                    )
                    flutter_packages_copied = True
                shutil.rmtree(flutter_dir)

            if compile_packages:
                with command._console.status(
                    f"[bold green]正在编译应用包 {site_packages_dir}[/bold green]"
                ):
                    subprocess.run(
                        [
                            str(command._target_python()),
                            "-m",
                            "compileall",
                            "-b",
                            str(site_packages_dir),
                        ],
                        check=True,
                    )
                command._verbose_log("删除原始 .py 文件")
                command.cleanup_dir(site_packages_dir, ["**.py"])

            if cleanup_globs:
                command._verbose_log(f"删除不必要的包文件和目录: {cleanup_globs}")
                with command._console.status("[bold green]清理已安装的包..."):
                    command.cleanup_dir(site_packages_dir, cleanup_globs)
        finally:
            command._verbose_log(f"删除 sitecustomize 目录 {temporary_dir}")
    return flutter_packages_copied


def install_native_dependencies(
    command,
    *,
    platform: str,
    architectures: list[str],
    requirements: list[str],
    build_dir: Path,
    pip_tool: str,
    compile_packages: bool,
    cleanup_globs: list[str],
) -> None:
    command._header("安装依赖包")
    site_packages_root = os.environ.get(site_packages_env_var) or os.environ.get(
        legacy_site_packages_env_var
    )
    if not site_packages_root:
        site_packages_root = build_dir / default_site_packages_dir
    site_packages_root = Path(site_packages_root)
    command._clear_package_directory(site_packages_root)

    install_architectures = architectures if requirements else []
    flutter_packages_copied = False
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=command._console,
    ) as progress:
        task = progress.add_task("安装依赖...", total=len(install_architectures))
        for architecture in install_architectures:
            progress.update(
                task,
                description=f"处理架构 [cyan]{architecture}[/cyan]...",
            )
            destination = site_packages_root
            if architecture:
                destination /= architecture
            flutter_packages_copied = command._install_arch_dependencies(
                platform=platform,
                architecture=architecture,
                requirements=requirements,
                site_packages_dir=destination,
                pip_tool=pip_tool,
                compile_packages=compile_packages,
                cleanup_globs=cleanup_globs,
                flutter_packages_copied=flutter_packages_copied,
            )
            progress.update(task, advance=1)

    if platform == "Darwin" and install_architectures:
        macos_utils.merge_macos_site_packages(
            str(site_packages_root / "arm64"),
            str(site_packages_root / "x86_64"),
            str(site_packages_root),
            command._verbose,
        )
    sync_script = site_packages_root / ".pod" / "sync_site_packages.sh"
    if sync_script.exists():
        command.run_exec("/bin/sh", [str(sync_script)])
