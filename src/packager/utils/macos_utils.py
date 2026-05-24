import shutil
import subprocess
import sys
from pathlib import Path


def merge_macos_site_packages(
    arm64_path: str, x86_64_path: str, target_path: str, verbose: bool
) -> None:
    arm64_dir = Path(arm64_path)
    x86_64_dir = Path(x86_64_path)
    target_dir = Path(target_path)

    # Create the target directory if it doesn't exist
    if not target_dir.exists():
        target_dir.mkdir(parents=True, exist_ok=True)

    # Merge the directories
    if x86_64_dir.exists() and not arm64_dir.exists():
        print("复制包 macOS(x86_64) -> site-packages ...")
        copy_directory(x86_64_dir, target_dir)
    elif arm64_dir.exists() and not x86_64_dir.exists():
        print("复制包 macOS(arm64) -> site-packages ...")
        copy_directory(arm64_dir, target_dir)
    elif arm64_dir.exists() and x86_64_dir.exists():
        print("合并包 macOS(arm64) 和 macOS(x86_64) -> site-packages ...")
        merge_dirs(arm64_dir, x86_64_dir, target_dir, verbose)
    else:
        print("无法合并 macOS 包，未找到架构目录")
        sys.exit(1)

    if arm64_dir.exists():
        shutil.rmtree(str(arm64_dir))

    if x86_64_dir.exists():
        shutil.rmtree(str(x86_64_dir))

    print("成功合并 macOS 包")


def merge_dirs(
    arm64_dir: Path, x86_64_dir: Path, target_dir: Path, verbose: bool
) -> None:
    # Create the destination directory if it doesn't exist
    if not target_dir.exists():
        target_dir.mkdir(parents=True, exist_ok=True)

    # Iterate over the items in the arm64 directory
    for item in arm64_dir.rglob("*"):
        rel = item.relative_to(arm64_dir)
        x8664_item_path = x86_64_dir / rel
        target_item_path = target_dir / rel

        if item.is_file():
            if not target_item_path.parent.exists():
                target_item_path.parent.mkdir(parents=True, exist_ok=True)
            if item.suffix == ".so":
                if is_universal_binary(str(item)):
                    if verbose:
                        print(
                            f"{item} 已经是一个通用二进制文件，复制中..."
                        )
                    shutil.copy2(str(item), str(target_item_path))
                elif is_universal_binary(str(x8664_item_path)):
                    if verbose:
                        print(
                            f"{item} 已经是一个通用二进制文件，复制中..."
                        )
                    shutil.copy2(str(x8664_item_path), str(target_item_path))
                else:
                    if verbose:
                        print(f"正在合并 {item} 和 {x8664_item_path}...")
                    lipo(
                        str(item),
                        str(x8664_item_path),
                        str(target_item_path),
                    )
            else:
                # Copy non-.so files
                if verbose:
                    print(f"复制 {item}...")
                shutil.copy2(str(item), str(target_item_path))


def copy_directory(source: Path, destination: Path) -> None:
    print(f"复制目录 {source} -> {destination}")
    if not destination.exists():
        destination.mkdir(parents=True, exist_ok=True)

    for entity in source.rglob("*"):
        rel = entity.relative_to(source)
        new_path = destination / rel
        if entity.is_dir():
            new_path.mkdir(parents=True, exist_ok=True)
        elif entity.is_file():
            shutil.copy2(str(entity), str(new_path))


def is_universal_binary(file_path: str) -> bool:
    result = subprocess.run(["file", file_path], capture_output=True, text=True)
    return "arm64" in result.stdout and "x86_64" in result.stdout


def lipo(arm64_path: str, x86_64_path: str, output_path: str) -> None:
    subprocess.run(
        ["lipo", "-create", "-output", output_path, arm64_path, x86_64_path]
    )
