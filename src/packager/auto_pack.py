import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
EDIR = Path.home() / "pyrite-project" / "pyrite-ide-plugin-example"
WHEEL_DIR = EDIR / "lib" / "wheel"
ASSETS_PYTHON = EDIR / "assets" / "macos" / "python"
DIST_DIR = PROJECT_ROOT / "dist"
PYTHON_ZIP = EDIR / "assets" / "macos" / "python.zip"
BUILD_DIR = EDIR / "build"
SITE_PACKAGES_ROOT = BUILD_DIR / "site-packages"

# Mirrors serious_python's sitecustomize.py for per-architecture pip installs.
SITECUSTOMIZE_PY = '''\
custom_system = ""
custom_platform = ""
custom_mac_ver = "{mac_ver}"

import platform as _platform
import sysconfig as _sysconfig

if custom_system:
    _platform.system = lambda: custom_system
if custom_platform:
    _sysconfig.get_platform = lambda: custom_platform
if custom_mac_ver:
    _orig_mac_ver = _platform.mac_ver
    def _custom_mac_ver():
        orig = _orig_mac_ver()
        return orig[0], orig[1], custom_mac_ver
    _platform.mac_ver = _custom_mac_ver
'''


def print_step(step: int | str, msg: str):
    print(f"\n{'='*60}")
    print(f"[Step {step}] {msg}")
    print(f"{'='*60}")


def run_cmd(cmd: list[str], cwd: Path):
    print(f"  Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        print(f"  FAILED (exit code {result.returncode})", file=sys.stderr)
        sys.exit(result.returncode)


def merge_macos_archs(arm64_dir: Path, x86_64_dir: Path, target_dir: Path):
    """Merge arm64 and x86_64 site-packages, using lipo for .so files."""
    target_dir.mkdir(parents=True, exist_ok=True)

    if x86_64_dir.exists() and not arm64_dir.exists():
        print("  Copying macOS x86_64 site-packages")
        shutil.copytree(x86_64_dir, target_dir, dirs_exist_ok=True)
    elif arm64_dir.exists() and not x86_64_dir.exists():
        print("  Copying macOS arm64 site-packages")
        shutil.copytree(arm64_dir, target_dir, dirs_exist_ok=True)
    elif arm64_dir.exists() and x86_64_dir.exists():
        print("  Merging macOS arm64 and x86_64 site-packages")
        arm64_files = {str(f.relative_to(arm64_dir)): f
                       for f in arm64_dir.rglob("*") if f.is_file()}
        x86_files = {str(f.relative_to(x86_64_dir)): f
                      for f in x86_64_dir.rglob("*") if f.is_file()}
        all_rel = set(arm64_files) | set(x86_files)

        for rel in sorted(all_rel):
            arm64_path = arm64_files.get(rel)
            x86_path = x86_files.get(rel)
            src = arm64_path or x86_path
            if src is None:
                continue
            dest = target_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)

            if src.suffix == ".so" and arm64_path and x86_path:
                if _is_universal(arm64_path):
                    shutil.copy2(arm64_path, dest)
                elif _is_universal(x86_path):
                    shutil.copy2(x86_path, dest)
                else:
                    print(f"    lipo: {rel}")
                    try:
                        subprocess.run(
                            ["lipo", "-create", "-output", str(dest),
                             str(arm64_path), str(x86_path)],
                            check=True, capture_output=True, text=True)
                    except subprocess.CalledProcessError as e:
                        print(f"    lipo failed: {e.stderr.strip()}, "
                              "falling back to arm64")
                        shutil.copy2(arm64_path, dest)
            else:
                shutil.copy2(src, dest)

    for d in [arm64_dir, x86_64_dir]:
        if d.exists():
            shutil.rmtree(d)

    print("  Merging completed.")


def _is_universal(filepath: Path) -> bool:
    result = subprocess.run(["file", str(filepath)], capture_output=True, text=True)
    return "arm64" in result.stdout and "x86_64" in result.stdout


def setup_site_packages_uv(requirements_file: Path, wheel_dir: Path, verbose: bool = False):
    """Install packages via uv pip install for arm64 and x86_64, then merge."""
    archs = {
        "arm64": "aarch64-apple-darwin",
        "x86_64": "x86_64-apple-darwin",
    }

    for arch_name, uv_platform in archs.items():
        site_packages_dir = SITE_PACKAGES_ROOT / arch_name
        site_packages_dir.mkdir(parents=True, exist_ok=True)

        # Clear old packages (skip dotfiles)
        for item in list(site_packages_dir.iterdir()):
            if not item.name.startswith("."):
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

        # Write sitecustomize.py so any pip-invoked Python subprocesses
        # use the target architecture.
        sitecustomize_dir = Path(tempfile.mkdtemp(prefix="sp_sitecustomize_"))
        (sitecustomize_dir / "sitecustomize.py").write_text(
            SITECUSTOMIZE_PY.format(mac_ver=arch_name))

        env = os.environ.copy()
        pp = str(sitecustomize_dir)
        if "PYTHONPATH" in env:
            pp = f"{pp}:{env['PYTHONPATH']}"
        env["PYTHONPATH"] = pp

        cmd = [
            "uv", "pip", "install",
            "--target", str(site_packages_dir),
            "--python-platform", uv_platform,
            "--python", "3.12",
            "--pre",
            "-r", str(requirements_file),
            "--find-links", str(wheel_dir),
            "--extra-index-url", "https://pypi.flet.dev",
            "--index-strategy", "unsafe-best-match",
        ]
        if verbose:
            cmd.append("--verbose")

        print(f"  Installing packages for {arch_name} ({uv_platform}) ...")
        if verbose:
            print(f"    Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, env=env, cwd=EDIR)
        shutil.rmtree(sitecustomize_dir)
        if result.returncode != 0:
            print(f"  FAILED (exit code {result.returncode})", file=sys.stderr)
            sys.exit(result.returncode)

    merge_macos_archs(
        SITE_PACKAGES_ROOT / "arm64",
        SITE_PACKAGES_ROOT / "x86_64",
        SITE_PACKAGES_ROOT,
    )


def main():
    # Step 1: Copy example.py to lib/__main__.py as the plugin entry point
    print_step(1, "Copy example.py to lib/__main__.py")
    lib_dir = EDIR / "lib"
    lib_dir.mkdir(parents=True, exist_ok=True)
    src_main = PROJECT_ROOT / "examples" / "example.py"
    dst_main = lib_dir / "__main__.py"
    shutil.copy2(src_main, dst_main)
    print(f"  Copied: {src_main} -> {dst_main}")

    # Step 2: Build the wheel
    print_step(2, "Build wheel")
    run_cmd([sys.executable, "-m", "build"], cwd=PROJECT_ROOT)

    # Step 3: Copy whl to IDE plugin wheel directory
    print_step(3, "Copy whl to IDE plugin example")
    WHEEL_DIR.mkdir(parents=True, exist_ok=True)
    whl_files = sorted(DIST_DIR.glob("*.whl"))
    if not whl_files:
        print("ERROR: no .whl files found in dist/", file=sys.stderr)
        sys.exit(1)
    latest_whl = whl_files[-1]

    # Remove old whl files
    for old_whl in WHEEL_DIR.glob("*.whl"):
        old_whl.unlink()
        print(f"  Removed old: {old_whl.name}")

    shutil.copy2(latest_whl, WHEEL_DIR / latest_whl.name)
    print(f"  Copied: {latest_whl.name} -> {WHEEL_DIR}")

    # Step 4: Install site-packages via uv (replaces dart serious_python)
    print_step(4, "Install site-packages via uv for arm64 + x86_64")
    reqs_file = EDIR / "lib" / "requirements.txt"
    setup_site_packages_uv(reqs_file, WHEEL_DIR, verbose=True)

    # Step 5: Copy lib/ and site-packages into assets/macos/python/
    print_step(5, "Assemble final python bundle")
    if ASSETS_PYTHON.exists():
        shutil.rmtree(ASSETS_PYTHON)
    ASSETS_PYTHON.mkdir(parents=True)

    # Copy app code from lib/ (skip wheel/, requirements.txt)
    app_src = EDIR / "lib"
    for item in app_src.iterdir():
        if item.name in ("wheel", "requirements.txt"):
            continue
        dest = ASSETS_PYTHON / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)
    print(f"  Copied app code from {app_src}")

    # Copy site-packages
    site_packages_dst = ASSETS_PYTHON / "site-packages"
    if SITE_PACKAGES_ROOT.exists():
        if site_packages_dst.exists():
            shutil.rmtree(site_packages_dst)
        shutil.copytree(SITE_PACKAGES_ROOT, site_packages_dst)
        print(f"  Copied site-packages: {SITE_PACKAGES_ROOT}")
    else:
        print(f"ERROR: {SITE_PACKAGES_ROOT} not found", file=sys.stderr)
        sys.exit(1)

    # Step 6: Package final python.zip
    print_step(6, "Package final python.zip")
    if PYTHON_ZIP.exists():
        PYTHON_ZIP.unlink()

    with zipfile.ZipFile(PYTHON_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for entry in ASSETS_PYTHON.iterdir():
            if entry.is_dir():
                for file_path in entry.rglob("*"):
                    if file_path.is_file():
                        zf.write(file_path, file_path.relative_to(ASSETS_PYTHON))
            elif entry.is_file():
                zf.write(entry, entry.relative_to(ASSETS_PYTHON))
    print(f"  Created: {PYTHON_ZIP}")

    # Cleanup
    print_step("Cleanup", "Remove temporary python directory")
    shutil.rmtree(ASSETS_PYTHON)
    print("  Done.")

    print(f"\n{'='*60}")
    print("All steps completed successfully!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
