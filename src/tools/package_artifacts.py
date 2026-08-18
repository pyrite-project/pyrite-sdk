from __future__ import annotations

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
import urllib.request
import zipfile
from collections.abc import Callable
from pathlib import Path

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)

from .package_installer import (
    architectures,
    default_site_packages_dir,
    platforms,
    runtime_metadata_filename,
)
from .python_versions import PythonRelease


def archive_destination(
    destination: Path,
    architecture: str,
    platform: str | None = None,
) -> Path:
    stem = "-".join(filter(None, (destination.stem, platform, architecture)))
    return destination.with_name(f"{stem}{destination.suffix}")


def archive_family(destination: Path, platform: str | None = None) -> set[Path]:
    if platform:
        return {
            destination,
            archive_destination(destination, "", platform),
            *(
                archive_destination(destination, architecture, platform)
                for architecture in architectures
            ),
        }
    return {
        destination,
        *(
            archive_destination(destination, architecture)
            for architecture in architectures
        ),
    }


def archive_outputs(destination: Path) -> set[Path]:
    return {
        destination,
        *(
            archive_destination(destination, architecture, platform)
            for platform in platforms
            for architecture in ("", *architectures)
        ),
    }


def flatten_architecture_package_dir(
    package_dir: Path,
    architecture: str,
) -> None:
    site_packages_dir = package_dir / default_site_packages_dir
    selected_dir = site_packages_dir / architecture
    if architecture and selected_dir.is_dir():
        shutil.copytree(selected_dir, site_packages_dir, dirs_exist_ok=True)
    for known_architecture in architectures:
        architecture_dir = site_packages_dir / known_architecture
        if architecture_dir.is_dir():
            shutil.rmtree(architecture_dir)
        elif architecture_dir.exists():
            architecture_dir.unlink()


def publish_archive_family(
    destination: Path,
    staged_archives: list[tuple[Path, Path]],
    platform: str | None = None,
) -> None:
    family_files = {
        candidate
        for archive in archive_family(destination, platform)
        for candidate in (archive, Path(f"{archive}.hash"))
    }
    for candidate in sorted(family_files, key=str):
        try:
            mode = candidate.lstat().st_mode
        except FileNotFoundError:
            continue
        if not stat.S_ISREG(mode):
            raise ValueError(f"Archive output path is not a regular file: {candidate}")

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
            produced_archives = {archive_dest for _, archive_dest in staged_archives}
            for archive in archive_family(destination, platform) - produced_archives:
                archive.unlink(missing_ok=True)
                Path(f"{archive}.hash").unlink(missing_ok=True)
        except Exception as publish_error:
            rollback_errors: list[Exception] = []
            for candidate in family_files:
                try:
                    candidate.unlink(missing_ok=True)
                except Exception as error:  # noqa: BLE001
                    rollback_errors.append(error)
            for candidate, backup in backups.items():
                try:
                    shutil.copy2(backup, candidate)
                except Exception as error:  # noqa: BLE001
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
            except Exception:  # noqa: BLE001, S110
                pass


def write_runtime_metadata(
    package_dir: Path,
    release: PythonRelease,
    *,
    platform: str,
    architectures: list[str],
) -> None:
    metadata = {
        "schema_version": 1,
        "runtime": {
            "implementation": "cpython",
            "python_version": release.short_version,
            "python_full_version": release.full_version,
        },
        "target": {
            "platform": platform,
            "architectures": [value for value in architectures if value],
        },
    }
    (package_dir / runtime_metadata_filename).write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )


def clear_package_directory(directory: Path) -> None:
    if not directory.exists():
        return
    for entry in directory.iterdir():
        if entry.name.startswith("."):
            continue
        if entry.is_dir():
            shutil.rmtree(entry)
        else:
            entry.unlink()


def copy_directory_with_progress(
    source: Path,
    destination: Path,
    root_dir: str,
    exclude_list: list,
    console: Console,
    excluded_roots: list[Path] | None = None,
) -> None:
    resolved_excluded_roots = [
        excluded_root.resolve() for excluded_root in (excluded_roots or [])
    ]
    all_files = [
        file
        for file in source.rglob("*")
        if file.is_file()
        and str(file.relative_to(root_dir)) not in exclude_list
        and not any(
            file.resolve().is_relative_to(excluded_root)
            for excluded_root in resolved_excluded_roots
        )
    ]
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("复制文件...", total=len(all_files))
        for file in all_files:
            destination_file = destination / file.relative_to(source)
            destination_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, destination_file)
            progress.update(task, advance=1)


def copy_directory(
    source: Path,
    destination: Path,
    root_dir: str,
    exclude_list: list,
) -> None:
    for entity in source.iterdir():
        if str(entity.relative_to(root_dir)) in exclude_list:
            continue
        target = destination / entity.name
        if entity.is_dir():
            target.mkdir(exist_ok=True)
            copy_directory(entity, target, root_dir, exclude_list)
        elif entity.is_file():
            shutil.copy2(entity, target)


def cleanup_directory(
    directory: Path,
    globs: list,
    verbose_log: Callable[[str], None],
) -> bool:
    empty_dir = True
    for entity in list(directory.iterdir()):
        matches = any(
            fnmatch.fnmatch(
                str(entity).replace("\\", "/"),
                pattern.replace("\\", "/"),
            )
            for pattern in globs
        )
        if matches and entity.exists():
            verbose_log(f"删除 {entity}")
            if entity.is_dir():
                shutil.rmtree(entity)
            else:
                entity.unlink()
        elif entity.is_dir():
            if cleanup_directory(entity, globs, verbose_log):
                verbose_log(f"删除空目录 {entity}")
                entity.rmdir()
            else:
                empty_dir = False
        else:
            empty_dir = False
    return empty_dir


def run_exec(
    executable: str,
    args: list,
    console: Console,
    verbose_log: Callable[[str], None],
    environment: dict | None = None,
) -> int:
    env = os.environ.copy()
    if environment:
        env.update({key: str(value) for key, value in environment.items()})
    process = subprocess.Popen(
        [executable, *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    assert process.stdout is not None
    for line in process.stdout:
        verbose_log(line.strip())
    _, stderr_text = process.communicate()
    if process.returncode != 0:
        console.print(f"[red]{stderr_text}[/red]")
        sys.exit(1)
    return process.returncode


def zip_directory_posix(
    source: Path,
    destination: Path,
    progress: Progress | None = None,
    task_id: TaskID | None = None,
) -> None:
    all_files = [file for file in source.rglob("*") if file.is_file()]
    if progress and task_id is not None:
        progress.update(task_id, total=len(all_files))
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in all_files:
            archive.write(file, "/".join(file.relative_to(source).parts))
            if progress and task_id is not None:
                progress.update(task_id, advance=1)


def calculate_file_hash(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_archives(
    command,
    *,
    app_dir: Path,
    destination: Path,
    platform: str,
    architectures: list[str],
    requirements: list[str],
    skip_site_packages: bool,
    pip_tool: str,
    compile_packages: bool,
    cleanup_globs: list[str],
) -> list[Path]:
    command._header("创建应用存档")
    archive_destinations: list[Path] = []
    staged_archives: list[tuple[Path, Path]] = []
    flutter_packages_copied = False
    try:
        for architecture in architectures:
            package_dir = Path(tempfile.mkdtemp(prefix="pyrite_plugin_package"))
            try:
                command.copy_directory(app_dir, package_dir, str(app_dir), [])
                command._flatten_architecture_package_dir(package_dir, architecture)
                if requirements and not skip_site_packages:
                    site_packages_dir = package_dir / default_site_packages_dir
                    command._clear_package_directory(site_packages_dir)
                    flutter_packages_copied = command._install_arch_dependencies(
                        platform=platform,
                        architecture=architecture,
                        requirements=requirements,
                        site_packages_dir=site_packages_dir,
                        pip_tool=pip_tool,
                        compile_packages=compile_packages,
                        cleanup_globs=cleanup_globs,
                        flutter_packages_copied=flutter_packages_copied,
                    )
                command._write_runtime_metadata(
                    package_dir,
                    platform=platform,
                    architectures=[architecture],
                )
                archive_dest = command._archive_destination(
                    destination,
                    architecture,
                    platform=platform,
                )
                descriptor, archive_name = tempfile.mkstemp(
                    prefix="pyrite_plugin_archive",
                    suffix=".pyrix",
                    dir=destination.parent,
                )
                os.close(descriptor)
                staged_archive = Path(archive_name)
                staged_archives.append((staged_archive, archive_dest))
                command._create_archive(
                    package_dir,
                    staged_archive,
                    reported_destination=archive_dest,
                )
                archive_destinations.append(archive_dest)
            finally:
                if package_dir.exists():
                    shutil.rmtree(package_dir)
        command._publish_archive_family(
            destination,
            staged_archives,
            platform=platform,
        )
    finally:
        for staged_archive, _ in staged_archives:
            staged_archive.unlink(missing_ok=True)
            Path(f"{staged_archive}.hash").unlink(missing_ok=True)
    return archive_destinations


def resolve_target_python(
    build_dir: Path,
    release: PythonRelease,
    log: Callable[[str], None],
) -> tuple[Path, Path]:
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

    archive_name = (
        f"cpython-{release.full_version}+{release.standalone_release_date}"
        f"-{archive_arch}-install_only_stripped.tar.gz"
    )
    python_dir = build_dir / (
        f"build_python_{release.full_version}-{release.standalone_release_date}"
    )
    build_id = f"{release.full_version}-{release.standalone_release_date}"
    marker = python_dir / ".python_build_id"
    if not (python_dir.exists() and marker.exists() and marker.read_text() == build_id):
        cache_root = os.environ.get("FLET_CACHE_DIR")
        if cache_root:
            cache_base = Path(cache_root)
        else:
            home = os.environ.get("USERPROFILE") or os.environ.get(
                "HOME", str(build_dir)
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
            temporary_archive = archive_path.with_suffix(archive_path.suffix + ".tmp")
            log(f"下载 Python runtime: [dim]{url}[/dim]")
            try:
                with (
                    urllib.request.urlopen(url) as response,
                    temporary_archive.open("wb") as output,
                ):
                    if getattr(response, "status", 200) != 200:
                        raise RuntimeError(f"下载失败，HTTP {response.status}")
                    shutil.copyfileobj(response, output)
                os.replace(temporary_archive, archive_path)
            finally:
                if temporary_archive.exists():
                    temporary_archive.unlink()

        staging_dir = python_dir.with_name(f"{python_dir.name}.tmp")
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        staging_dir.mkdir(parents=True)
        try:
            with tarfile.open(archive_path, "r:gz") as archive:
                archive.extractall(staging_dir, filter="data")
            (staging_dir / ".python_build_id").write_text(
                build_id,
                encoding="ascii",
            )
            if python_dir.exists():
                shutil.rmtree(python_dir)
            os.replace(staging_dir, python_dir)
        finally:
            if staging_dir.exists():
                shutil.rmtree(staging_dir)

    if host_platform.system() == "Windows":
        executable = python_dir / "python" / "python.exe"
    else:
        executable = python_dir / "python" / "bin" / "python3"
    if not executable.exists():
        raise RuntimeError(f"Python runtime 缺少解释器: {executable}")
    return executable, python_dir
