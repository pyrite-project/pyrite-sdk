"""Synchronize the SDK version table with Serious Python's JSON output."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


SDK_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = SDK_ROOT / "src" / "tools" / "_python_versions_data.py"
DEFAULT_PLUGIN_PYTHON_VERSION = "3.14"
DEFAULT_SERIOUS_PYTHON_DIR = (
    SDK_ROOT.parent
    / "pyrite-ide"
    / "python_runtime"
    / "src"
    / "serious_python"
)


def _load_document(
    input_path: Path | None,
    serious_python_dir: Path,
    dart_executable: str | None,
) -> dict[str, Any]:
    if input_path is not None:
        return json.loads(input_path.read_text(encoding="utf-8"))

    dart = dart_executable or shutil.which("dart")
    if dart is None:
        raise FileNotFoundError(
            "Dart was not found. Pass --dart or use --input with saved version JSON."
        )
    result = subprocess.run(
        [dart, "run", "serious_python:main", "version", "--json"],
        cwd=serious_python_dir,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(result.stdout)


def _required_string(document: dict[str, Any], key: str) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Serious Python version JSON has no valid {key!r}")
    return value


def _release_data(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw_releases = document.get("python_releases")
    if not isinstance(raw_releases, dict) or not raw_releases:
        raise ValueError("Serious Python version JSON has no Python releases")

    releases: dict[str, dict[str, Any]] = {}
    for short_version, raw_release in raw_releases.items():
        if not isinstance(short_version, str) or not isinstance(raw_release, dict):
            raise ValueError("Serious Python version JSON has an invalid release")
        android_abis = raw_release.get("android_abis")
        if not isinstance(android_abis, list) or not all(
            isinstance(abi, str) and abi for abi in android_abis
        ):
            raise ValueError(
                f"Serious Python release {short_version} has no valid android_abis"
            )
        releases[short_version] = {
            "full_version": _required_string(raw_release, "standalone_version"),
            "standalone_release_date": _required_string(
                raw_release, "standalone_release_date"
            ),
            "android_abis": tuple(android_abis),
            "prerelease": raw_release.get("prerelease") is True,
        }
    return releases


def _python_literal(value: Any, indent: int = 0) -> str:
    prefix = " " * indent
    if isinstance(value, dict):
        lines = ["{"]
        for key, item in value.items():
            rendered = _python_literal(item, indent + 4)
            lines.append(f"{' ' * (indent + 4)}{key!r}: {rendered},")
        lines.append(f"{prefix}}}")
        return "\n".join(lines)
    return repr(value)


def render_version_data(document: dict[str, Any]) -> str:
    serious_python_version = _required_string(document, "serious_python_version")
    build_release_date = _required_string(document, "python_build_release_date")
    releases = _release_data(document)
    if DEFAULT_PLUGIN_PYTHON_VERSION not in releases:
        raise ValueError(
            "SDK default Python version "
            f"{DEFAULT_PLUGIN_PYTHON_VERSION} is not in python_releases"
        )

    return (
        '"""Generated from Serious Python\'s machine-readable version manifest."""\n\n'
        f"SERIOUS_PYTHON_VERSION = {serious_python_version!r}\n"
        f"PYTHON_BUILD_RELEASE_DATE = {build_release_date!r}\n\n"
        f"PYTHON_RELEASE_DATA = {_python_literal(releases)}\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    parser.add_argument("--dart")
    parser.add_argument(
        "--serious-python-dir",
        type=Path,
        default=DEFAULT_SERIOUS_PYTHON_DIR,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    document = _load_document(args.input, args.serious_python_dir, args.dart)
    generated = render_version_data(document)
    if args.check:
        if (
            not args.output.is_file()
            or args.output.read_text(encoding="utf-8") != generated
        ):
            print(f"Serious Python version data is stale: {args.output}", file=sys.stderr)
            return 1
        return 0

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(generated, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
