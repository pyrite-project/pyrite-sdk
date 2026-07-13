"""Bundled Python versions synchronized with serious_python 4.3.2."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

DEFAULT_PYTHON_VERSION = "3.14"
PYTHON_RELEASE_DATE = "20260712"


@dataclass(frozen=True)
class PythonRelease:
    short_version: str
    full_version: str
    standalone_release_date: str
    android_abis: tuple[str, ...]
    prerelease: bool = False


PYTHON_RELEASES: dict[str, PythonRelease] = {
    "3.12": PythonRelease(
        short_version="3.12",
        full_version="3.12.13",
        standalone_release_date="20260623",
        android_abis=("arm64-v8a", "x86_64", "armeabi-v7a"),
    ),
    "3.13": PythonRelease(
        short_version="3.13",
        full_version="3.13.14",
        standalone_release_date="20260623",
        android_abis=("arm64-v8a", "x86_64", "armeabi-v7a"),
    ),
    "3.14": PythonRelease(
        short_version="3.14",
        full_version="3.14.6",
        standalone_release_date="20260623",
        android_abis=("arm64-v8a", "x86_64", "armeabi-v7a"),
    ),
}


def resolve_python_release(
    requested: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> PythonRelease:
    env = os.environ if environ is None else environ
    short_version = requested or env.get("SERIOUS_PYTHON_VERSION")
    short_version = short_version or DEFAULT_PYTHON_VERSION
    try:
        base = PYTHON_RELEASES[short_version]
    except KeyError as exc:
        supported = ", ".join(PYTHON_RELEASES)
        raise ValueError(
            f"Unknown Python version: {short_version}. Supported: {supported}"
        ) from exc

    return PythonRelease(
        short_version=base.short_version,
        full_version=env.get("SERIOUS_PYTHON_FULL_VERSION", base.full_version),
        standalone_release_date=env.get(
            "SERIOUS_PYTHON_DIST_RELEASE", base.standalone_release_date
        ),
        android_abis=base.android_abis,
        prerelease=base.prerelease,
    )
