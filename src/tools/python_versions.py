"""Bundled Python versions synchronized with Serious Python."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Mapping

from ._python_versions_data import (
    PYTHON_BUILD_RELEASE_DATE,
    PYTHON_RELEASE_DATA,
)

PYTHON_RELEASE_DATE = PYTHON_BUILD_RELEASE_DATE
DEFAULT_PLUGIN_PYTHON_VERSION = "3.14"


@dataclass(frozen=True)
class PythonRelease:
    short_version: str
    full_version: str
    standalone_release_date: str
    android_abis: tuple[str, ...]
    prerelease: bool = False


PYTHON_RELEASES: dict[str, PythonRelease] = {
    short_version: PythonRelease(short_version=short_version, **release)
    for short_version, release in PYTHON_RELEASE_DATA.items()
}

if DEFAULT_PLUGIN_PYTHON_VERSION not in PYTHON_RELEASES:
    raise RuntimeError(
        f"Default plugin Python {DEFAULT_PLUGIN_PYTHON_VERSION} is not supported"
    )


def resolve_python_release(
    requested: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> PythonRelease:
    env = os.environ if environ is None else environ
    short_version = (
        DEFAULT_PLUGIN_PYTHON_VERSION if requested is None else requested
    )
    try:
        base = PYTHON_RELEASES[short_version]
    except KeyError as exc:
        supported = ", ".join(PYTHON_RELEASES)
        raise ValueError(
            f"Unknown Python version: {short_version}. Supported: {supported}"
        ) from exc

    full_version = env.get("SERIOUS_PYTHON_FULL_VERSION", base.full_version)
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:[a-zA-Z0-9.-]+)?", full_version):
        raise ValueError(f"Invalid CPython version: {full_version}")
    if not full_version.startswith(f"{base.short_version}."):
        raise ValueError(
            f"CPython version {full_version} does not match target "
            f"{base.short_version}"
        )

    standalone_release_date = env.get(
        "SERIOUS_PYTHON_DIST_RELEASE", base.standalone_release_date
    )
    if not re.fullmatch(r"\d{8}", standalone_release_date):
        raise ValueError(
            f"Invalid Python distribution release date: {standalone_release_date}"
        )

    return PythonRelease(
        short_version=base.short_version,
        full_version=full_version,
        standalone_release_date=standalone_release_date,
        android_abis=base.android_abis,
        prerelease=base.prerelease,
    )
