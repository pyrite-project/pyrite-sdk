import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
EDIR = Path.home() / "pyrite-project" / "pyrite-ide-plugin-example"
WHEEL_DIR = EDIR / "lib" / "wheel"
ASSETS_PYTHON = EDIR / "assets" / "macos" / "python"
DIST_DIR = PROJECT_ROOT / "dist"
PYTHON_ZIP = EDIR / "assets" / "macos" / "python.zip"


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

    # Step 4: Run dart serious_python package
    print_step(4, "Run dart serious_python:main package")
    run_cmd([
        "dart", "run", "serious_python:main", "package", "lib",
        "--platform", "Darwin",
        "--requirements", "--pre",
        "--requirements", "-rlib/requirements.txt",
        "--requirements", "--find-links=lib/wheel/",
        "--asset", "assets/macos/python.zip",
        "--verbose",
    ], cwd=EDIR)

    # Step 5: Unzip python.zip
    print_step(5, "Unzip python.zip")
    if not PYTHON_ZIP.exists():
        print(f"ERROR: {PYTHON_ZIP} not found", file=sys.stderr)
        sys.exit(1)

    # Remove existing python directory if present
    if ASSETS_PYTHON.exists():
        print("  Removing existing python directory")
        shutil.rmtree(ASSETS_PYTHON)

    if not ASSETS_PYTHON.exists():
        ASSETS_PYTHON.mkdir(parents=True)

    with zipfile.ZipFile(PYTHON_ZIP, "r") as zf:
        zf.extractall(ASSETS_PYTHON)
    print(f"  Extracted to {ASSETS_PYTHON}")

    # Step 6: Delete .dart_tool, requirements.txt, wheel/
    print_step(6, "Remove unwanted files from python directory")
    targets = [".dart_tool", "requirements.txt", "wheel"]
    for name in targets:
        target = ASSETS_PYTHON / name
        if target.is_dir():
            shutil.rmtree(target)
            print(f"  Removed directory: {name}")
        elif target.exists():
            target.unlink()
            print(f"  Removed file: {name}")
        else:
            print(f"  Skipped (not found): {name}")

    # Step 7: Copy build/site-packages to python directory
    print_step(7, "Copy site-packages to python directory")
    site_packages_src = EDIR / "build" / "site-packages"
    if not site_packages_src.exists():
        print(f"ERROR: {site_packages_src} not found", file=sys.stderr)
        sys.exit(1)

    site_packages_dst = ASSETS_PYTHON / "site-packages"
    if site_packages_dst.exists():
        shutil.rmtree(site_packages_dst)
    shutil.copytree(site_packages_src, site_packages_dst)
    print(f"  Copied: {site_packages_src} -> {site_packages_dst}")

    # Step 8: Repack python/* as zip
    print_step(8, "Repack python directory as python.zip")
    # Remove old zip
    if PYTHON_ZIP.exists():
        PYTHON_ZIP.unlink()
        print("  Removed old python.zip")

    with zipfile.ZipFile(PYTHON_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for entry in ASSETS_PYTHON.iterdir():
            if entry.is_dir():
                for file_path in entry.rglob("*"):
                    arcname = file_path.relative_to(ASSETS_PYTHON)
                    zf.write(file_path, arcname)
            else:
                arcname = entry.relative_to(ASSETS_PYTHON)
                zf.write(entry, arcname)
        print(f"  Created: {PYTHON_ZIP}")

    # Cleanup: remove the extracted python directory
    print_step("Cleanup", "Remove extracted python directory")
    shutil.rmtree(ASSETS_PYTHON)
    print("  Done.")

    print(f"\n{'='*60}")
    print("All steps completed successfully!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
