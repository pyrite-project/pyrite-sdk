import os
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from rich.console import Console

from packager.main import ARCH_MAP, PLATFORMS
from packager.package_command import (
    PackageCommand,
    app_environment_var,
    legacy_site_packages_env_var,
    platforms,
    site_packages_env_var,
)
from packager.python_versions import PYTHON_RELEASES, resolve_python_release
from packager.sitecustomize import sitecustomize_py


class PackagerRuntimeTest(unittest.TestCase):
    def test_supported_targets_and_android_tags_match_serious_python(self) -> None:
        self.assertEqual(PLATFORMS, ["Android", "Darwin", "Windows", "Linux"])
        self.assertEqual(
            ARCH_MAP["Android"],
            ["arm64-v8a", "armeabi-v7a", "x86_64"],
        )
        self.assertEqual(
            platforms["Android"],
            {
                "arm64-v8a": {"tag": "android-24-arm64_v8a", "mac_ver": ""},
                "armeabi-v7a": {
                    "tag": "android-24-armeabi_v7a",
                    "mac_ver": "",
                },
                "x86_64": {"tag": "android-24-x86_64", "mac_ver": ""},
            },
        )
        self.assertIn("platform.android_ver = custom_android_ver", sitecustomize_py)
        self.assertNotIn('custom_system == "iOS"', sitecustomize_py)

    def test_python_release_selection_and_overrides(self) -> None:
        self.assertEqual(list(PYTHON_RELEASES), ["3.12", "3.13", "3.14"])
        self.assertEqual(resolve_python_release().full_version, "3.14.6")
        self.assertEqual(
            resolve_python_release("3.12").full_version,
            "3.12.13",
        )
        overridden = resolve_python_release(
            environ={
                "SERIOUS_PYTHON_VERSION": "3.13",
                "SERIOUS_PYTHON_FULL_VERSION": "3.13.99",
                "SERIOUS_PYTHON_DIST_RELEASE": "20990101",
            }
        )
        self.assertEqual(overridden.full_version, "3.13.99")
        self.assertEqual(overridden.standalone_release_date, "20990101")

    def test_uv_remains_supported_and_uses_target_python(self) -> None:
        command = PackageCommand()
        target_python = Path("C:/runtime/python.exe")
        with patch.object(command, "_target_python", return_value=target_python):
            args = command._build_install_command(
                pip_tool="uv",
                pip_args=["--extra-index-url", "https://pypi.flet.dev"],
                site_packages_dir="build/site-packages",
                requirements=["pyrite-sdk"],
            )

        self.assertEqual(args[:3], ["uv", "pip", "install"])
        self.assertEqual(args[args.index("--python") + 1], str(target_python))
        self.assertIn("unsafe-best-match", args)

    def test_native_staging_defaults_site_packages_to_build_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "plugin"
            source.mkdir()
            (source / "__main__.py").write_text("print('ok')\n", encoding="utf-8")
            staging = root / "staged-app"
            site_packages = root / "build" / "site-packages"
            site_packages.mkdir(parents=True)
            stale_file = site_packages / "stale.pth"
            stale_file.write_text("stale\n", encoding="utf-8")

            previous_cwd = Path.cwd()
            try:
                os.chdir(root)
                with patch.dict(
                    os.environ,
                    {
                        app_environment_var: str(staging),
                        site_packages_env_var: "",
                        legacy_site_packages_env_var: "",
                    },
                    clear=False,
                ):
                    command = PackageCommand()
                    command._console = Console(file=StringIO(), force_terminal=False)
                    with (
                        patch.object(
                            command,
                            "_build_install_command",
                            return_value=["mock-install"],
                        ) as build_install_command,
                        patch("packager.package_command.subprocess.run") as run,
                    ):
                        run.return_value.returncode = 0
                        run.return_value.stdout = b""
                        run.return_value.stderr = b""
                        command.run(
                            source_dir=str(source),
                            platform="Windows",
                            arch=[],
                            requirements=["example-package"],
                            exclude=[],
                            cleanup_app_files=[],
                            cleanup_package_files=[],
                            python_version="3.14",
                        )

                self.assertEqual(
                    Path(
                        build_install_command.call_args.kwargs[
                            "site_packages_dir"
                        ]
                    ),
                    site_packages,
                )
                self.assertFalse(stale_file.exists())
                self.assertTrue((staging / "__main__.py").is_file())
            finally:
                os.chdir(previous_cwd)

    def test_native_app_staging_and_explicit_archive(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "plugin"
            source.mkdir()
            (source / "__main__.py").write_text("print('ok')\n", encoding="utf-8")
            staging = root / "staged-app"

            previous_cwd = Path.cwd()
            try:
                os.chdir(root)
                with patch.dict(
                    os.environ,
                    {
                        app_environment_var: str(staging),
                        site_packages_env_var: str(root / "site-packages"),
                    },
                    clear=False,
                ):
                    command = PackageCommand()
                    command._console = Console(file=StringIO(), force_terminal=False)
                    command.run(
                        source_dir=str(source),
                        platform="Windows",
                        arch=[],
                        requirements=[],
                        exclude=[],
                        skip_site_packages=True,
                        cleanup_app_files=[],
                        cleanup_package_files=[],
                        python_version="3.14",
                    )
                    self.assertTrue((staging / "__main__.py").is_file())

                    archive = root / "build" / "plugin.zip"
                    command = PackageCommand()
                    command._console = Console(file=StringIO(), force_terminal=False)
                    command.run(
                        source_dir=str(source),
                        platform="Windows",
                        arch=[],
                        requirements=[],
                        asset=str(archive.relative_to(root)),
                        exclude=[],
                        skip_site_packages=True,
                        cleanup_app_files=[],
                        cleanup_package_files=[],
                        python_version="3.14",
                    )
                    self.assertTrue(archive.is_file())
                    archive_hash = Path(f"{archive}.hash")
                    self.assertEqual(
                        archive_hash.read_text(),
                        command.calculate_file_hash(str(archive)),
                    )
            finally:
                os.chdir(previous_cwd)


if __name__ == "__main__":
    unittest.main()
