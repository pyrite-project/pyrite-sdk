import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from rich.console import Console

from pyrite_sdk.models.manifest import PluginManifestErrorCode, load_file
from tools.main import ARCH_MAP, PLATFORMS
from tools.package_command import (
    PackageCommand,
    app_environment_var,
    legacy_site_packages_env_var,
    platforms,
    runtime_metadata_filename,
    site_packages_env_var,
)
from tools.package_installer import (
    allow_source_distros_env_var,
    mobile_pypi_url,
)
from tools.python_versions import (
    DEFAULT_PLUGIN_PYTHON_VERSION,
    PYTHON_RELEASES,
    resolve_python_release,
)
from tools.sitecustomize import sitecustomize_py


def _manifest_v2(
    plugin_id: str = "fixture-plugin",
    *,
    python_version: str | None = None,
    extra: str = "",
) -> str:
    python_line = (
        "" if python_version is None else f'python_version = "{python_version}"\n'
    )
    return (
        "manifest_version = 2\n"
        f'id = "{plugin_id}"\n'
        f'name = "{plugin_id}"\n'
        'version = "1.1.0"\n'
        'type = "service"\n'
        "protocol_version = 1\n"
        f"{python_line}"
        "activation_events = []\n"
        "permissions = []\n"
        'platforms = ["windows", "linux", "macos", "android"]\n'
        f"{extra}"
    )


class PackagerRuntimeTest(unittest.TestCase):
    def test_archive_destination_appends_named_architecture(self) -> None:
        destination = Path("out/foo.bundle.pyrix")
        self.assertEqual(
            PackageCommand._archive_destination(destination, "arm64-v8a"),
            Path("out/foo.bundle-arm64-v8a.pyrix"),
        )
        self.assertEqual(
            PackageCommand._archive_destination(destination, ""),
            destination,
        )

    def test_default_archive_name_includes_architecture(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "plugin"
            source.mkdir()
            (source / "__main__.py").write_text(
                "print('ok')\n", encoding="utf-8"
            )
            (source / "plugin.toml").write_text(
                _manifest_v2(),
                encoding="utf-8",
            )

            previous_cwd = Path.cwd()
            try:
                os.chdir(root)
                command = PackageCommand()
                command._console = Console(file=StringIO(), force_terminal=False)
                command.run(
                    source_dir=str(source),
                    platform="Android",
                    arch=["arm64-v8a"],
                    requirements=[],
                    exclude=[],
                    skip_site_packages=True,
                    cleanup_app_files=[],
                    cleanup_package_files=[],
                )

                archive = root / "build" / "fixture-plugin-Android-arm64-v8a.pyrix"
                self.assertTrue(archive.is_file())
                self.assertTrue(Path(f"{archive}.hash").is_file())
                self.assertFalse(
                    (root / "build" / "fixture-plugin.pyrix").exists()
                )
            finally:
                os.chdir(previous_cwd)

    def test_templates_and_examples_use_valid_manifest_v2(self) -> None:
        expected_permissions = {
            "template-ui-plugin": ["ui.view"],
            "template-service-plugin": ["file.read"],
            "template-data-plugin": ["data.write"],
            "en-lang-pack": ["data.write"],
            "file-watcher": ["file.read"],
            "micropython-stubs-example": [
                "data.write",
                "settings.write",
                "ui.notify",
            ],
            "nord-theme": ["data.write"],
            "debug-enhanced": [
                "ui.view",
                "editor.read",
                "editor.write",
                "tab.create",
                "runtime.inspect",
            ],
        }
        manifests = [
            *Path("src/tools/template").rglob("plugin.toml"),
            *Path("examples").rglob("plugin.toml"),
        ]
        self.assertTrue(manifests)
        for path in manifests:
            with self.subTest(manifest=path):
                manifest = load_file(path)
                self.assertEqual(manifest.manifest_version, 2)
                self.assertEqual(manifest.python_version, "3.14")
                self.assertEqual(
                    manifest.permissions,
                    expected_permissions[manifest.id],
                )

    def test_packager_rejects_unsupported_manifests_with_stable_codes(self) -> None:
        fixture_root = Path("tests/fixtures/manifest_v2")
        cases = {
            "manifest_v1.toml": PluginManifestErrorCode.UNSUPPORTED_VERSION,
            "missing_version.toml": PluginManifestErrorCode.MISSING_VERSION,
            "rfw_renderer.toml": (
                PluginManifestErrorCode.RFW_RENDERER_UNSUPPORTED
            ),
        }
        for name, code in cases.items():
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, code):
                    PackageCommand._read_manifest(fixture_root / name)

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
        for release in PYTHON_RELEASES.values():
            with self.subTest(python_version=release.short_version):
                self.assertEqual(
                    set(release.android_abis),
                    set(platforms["Android"]),
                )
        self.assertIn("platform.android_ver = custom_android_ver", sitecustomize_py)
        self.assertNotIn('custom_system == "iOS"', sitecustomize_py)

    def test_python_release_selection_and_overrides(self) -> None:
        self.assertEqual(DEFAULT_PLUGIN_PYTHON_VERSION, "3.14")
        self.assertEqual(list(PYTHON_RELEASES), ["3.12", "3.13", "3.14"])
        self.assertEqual(resolve_python_release().full_version, "3.14.6")
        self.assertEqual(
            resolve_python_release("3.12").full_version,
            "3.12.13",
        )
        overridden = resolve_python_release(
            "3.13",
            environ={
                "SERIOUS_PYTHON_VERSION": "3.12",
                "SERIOUS_PYTHON_FULL_VERSION": "3.13.99",
                "SERIOUS_PYTHON_DIST_RELEASE": "20990101",
            }
        )
        self.assertEqual(overridden.short_version, "3.13")
        self.assertEqual(overridden.full_version, "3.13.99")
        self.assertEqual(overridden.standalone_release_date, "20990101")
        self.assertEqual(
            resolve_python_release(
                environ={"SERIOUS_PYTHON_VERSION": "3.12"}
            ).short_version,
            "3.14",
        )
        with self.assertRaisesRegex(ValueError, "does not match target 3.14"):
            resolve_python_release(
                "3.14",
                environ={"SERIOUS_PYTHON_FULL_VERSION": "3.13.99"},
            )
        with self.assertRaisesRegex(ValueError, "distribution release date"):
            resolve_python_release(
                "3.14",
                environ={"SERIOUS_PYTHON_DIST_RELEASE": "latest"},
            )

    def test_reused_command_selects_each_manifest_interpreter(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            expected_pythons: list[Path] = []
            sources: list[tuple[Path, str]] = []
            for version in ("3.12", "3.14"):
                release = resolve_python_release(version, environ={})
                source = root / f"plugin-{version}"
                source.mkdir()
                (source / "__main__.py").write_text(
                    "print('ok')\n", encoding="utf-8"
                )
                (source / "plugin.toml").write_text(
                    _manifest_v2(
                        f"fixture-{version}",
                        python_version=version,
                    ),
                    encoding="utf-8",
                )
                python_dir = (
                    root
                    / "build"
                    / (
                        f"build_python_{release.full_version}-"
                        f"{release.standalone_release_date}"
                    )
                )
                executable = python_dir / "python" / "python.exe"
                executable.parent.mkdir(parents=True)
                executable.touch()
                (python_dir / ".python_build_id").write_text(
                    (
                        f"{release.full_version}-"
                        f"{release.standalone_release_date}"
                    ),
                    encoding="ascii",
                )
                expected_pythons.append(executable)
                sources.append((source, version))

            previous_cwd = Path.cwd()
            try:
                os.chdir(root)
                command = PackageCommand()
                command._console = Console(file=StringIO(), force_terminal=False)
                with (
                    patch.dict(os.environ, {}, clear=True),
                    patch(
                        "tools.package_command.host_platform.system",
                        return_value="Windows",
                    ),
                    patch(
                        "tools.package_command.host_platform.machine",
                        return_value="AMD64",
                    ),
                    patch("tools.package_command.subprocess.run") as run,
                ):
                    run.return_value.returncode = 0
                    run.return_value.stdout = b""
                    run.return_value.stderr = b""
                    for source, version in sources:
                        command.run(
                            source_dir=str(source),
                            platform="Windows",
                            arch=[],
                            requirements=["example-package"],
                            asset=f"build/{version}.pyrix",
                            exclude=[],
                            cleanup_app_files=[],
                            cleanup_package_files=[],
                        )

                install_commands = [call.args[0] for call in run.call_args_list]
                self.assertEqual(len(install_commands), 2)
                self.assertEqual(
                    [
                        Path(args[args.index("--python") + 1])
                        for args in install_commands
                    ],
                    expected_pythons,
                )
            finally:
                os.chdir(previous_cwd)

    def test_uv_uses_target_python_and_explicit_target_platform(self) -> None:
        command = PackageCommand()
        target_python = Path("C:/runtime/python.exe")
        with patch.object(command, "_target_python", return_value=target_python):
            args = command._build_install_command(
                pip_tool="uv",
                pip_args=["--extra-index-url", "https://pypi.flet.dev"],
                site_packages_dir="build/site-packages",
                requirements=["pyrite-sdk"],
                platform="Android",
                arch="arm64-v8a",
            )

        self.assertEqual(args[:3], ["uv", "pip", "install"])
        self.assertEqual(args[args.index("--python") + 1], str(target_python))
        self.assertEqual(
            args[args.index("--python-platform") + 1],
            "aarch64-linux-android",
        )
        self.assertIn("unsafe-best-match", args)

    def test_uv_platform_mapping_and_armeabi_pip_fallback(self) -> None:
        command = PackageCommand()
        target_python = Path("C:/runtime/python.exe")
        cases = {
            ("Android", "x86_64"): "x86_64-linux-android",
            ("Darwin", "arm64"): "aarch64-apple-darwin",
            ("Darwin", "x86_64"): "x86_64-apple-darwin",
            ("Windows", ""): "windows",
            ("Linux", ""): "linux",
        }
        with patch.object(command, "_target_python", return_value=target_python):
            for (platform, arch), expected in cases.items():
                with self.subTest(platform=platform, arch=arch):
                    args = command._build_install_command(
                        pip_tool="uv",
                        pip_args=[],
                        site_packages_dir="build/site-packages",
                        requirements=["example-package"],
                        platform=platform,
                        arch=arch,
                    )
                    self.assertEqual(
                        args[args.index("--python-platform") + 1],
                        expected,
                    )

            fallback = command._build_install_command(
                pip_tool="uv",
                pip_args=[],
                site_packages_dir="build/site-packages",
                requirements=["example-package"],
                platform="Android",
                arch="armeabi-v7a",
            )

        self.assertEqual(
            fallback[:4],
            [str(target_python), "-m", "pip", "install"],
        )
        self.assertNotIn("--python-platform", fallback)

    def test_installer_applies_target_policy_and_isolates_environment(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            command = PackageCommand()
            command._console = Console(file=StringIO(), force_terminal=False)
            observed: dict[str, object] = {}

            def install(
                args: list[str],
                **kwargs: object,
            ) -> subprocess.CompletedProcess[bytes]:
                environment = kwargs["env"]
                self.assertIsInstance(environment, dict)
                assert isinstance(environment, dict)
                sitecustomize_dir = Path(environment["PYTHONPATH"])
                observed["sitecustomize_dir"] = sitecustomize_dir
                observed["sitecustomize"] = (
                    sitecustomize_dir / "sitecustomize.py"
                ).read_text(encoding="utf-8")
                observed["environment"] = environment
                return subprocess.CompletedProcess(args, 0, b"installed", b"")

            with (
                patch.dict(
                    os.environ,
                    {allow_source_distros_env_var: "source-package"},
                    clear=False,
                ),
                patch.object(
                    command,
                    "_build_install_command",
                    return_value=["mock-install"],
                ) as build_command,
                patch(
                    "tools.package_command.subprocess.run",
                    side_effect=install,
                ) as run,
            ):
                command._install_arch_dependencies(
                    platform="Android",
                    architecture="arm64-v8a",
                    requirements=["fixture-package"],
                    site_packages_dir=Path(temp) / "site-packages",
                    pip_tool="uv",
                    compile_packages=False,
                    cleanup_globs=[],
                    flutter_packages_copied=False,
                )

            self.assertEqual(
                build_command.call_args.kwargs["pip_args"],
                [
                    "--only-binary",
                    ":all:",
                    "--no-binary",
                    "source-package",
                    "--extra-index-url",
                    mobile_pypi_url,
                ],
            )
            environment = observed["environment"]
            self.assertIsInstance(environment, dict)
            self.assertEqual(environment["PYTHONNOUSERSITE"], "1")
            self.assertEqual(environment["PIP_REQUIRE_VIRTUALENV"], "false")
            self.assertIn("android-24-arm64_v8a", observed["sitecustomize"])
            self.assertFalse(observed["sitecustomize_dir"].exists())
            self.assertTrue(run.call_args.kwargs["capture_output"])
            self.assertFalse(run.call_args.kwargs["check"])

    def test_native_staging_defaults_site_packages_to_build_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "plugin"
            source.mkdir()
            (source / "__main__.py").write_text("print('ok')\n", encoding="utf-8")
            (source / "plugin.toml").write_text(
                _manifest_v2(),
                encoding="utf-8",
            )
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
                        patch("tools.package_command.subprocess.run") as run,
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
                metadata = json.loads(
                    (staging / runtime_metadata_filename).read_text(encoding="utf-8")
                )
                self.assertEqual(metadata["runtime"]["python_version"], "3.14")
                self.assertEqual(metadata["target"]["platform"], "Windows")
                self.assertEqual(metadata["target"]["architectures"], [])
            finally:
                os.chdir(previous_cwd)

    def test_native_app_staging_and_explicit_archive(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "plugin"
            source.mkdir()
            (source / "__main__.py").write_text("print('ok')\n", encoding="utf-8")
            (source / "plugin.toml").write_text(
                _manifest_v2(python_version="3.12"),
                encoding="utf-8",
            )
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
                    )
                    self.assertTrue((staging / "__main__.py").is_file())

                    archive_base = root / "build" / "plugin.pyrix"
                    archive = (
                        root
                        / "build"
                        / "fixture-plugin-Android-arm64-v8a.pyrix"
                    )
                    command = PackageCommand()
                    command._console = Console(file=StringIO(), force_terminal=False)
                    command.run(
                        source_dir=str(source),
                        platform="Android",
                        arch=["arm64-v8a"],
                        requirements=[],
                        asset=str(archive_base.relative_to(root)),
                        exclude=[],
                        skip_site_packages=True,
                        cleanup_app_files=[],
                        cleanup_package_files=[],
                    )
                    self.assertFalse(archive_base.exists())
                    self.assertTrue(archive.is_file())
                    with zipfile.ZipFile(archive) as package:
                        metadata = json.loads(
                            package.read(runtime_metadata_filename).decode("utf-8")
                        )
                    self.assertEqual(
                        metadata,
                        {
                            "schema_version": 1,
                            "runtime": {
                                "implementation": "cpython",
                                "python_version": "3.12",
                                "python_full_version": "3.12.13",
                            },
                            "target": {
                                "platform": "Android",
                                "architectures": ["arm64-v8a"],
                            },
                        },
                    )
                    archive_hash = Path(f"{archive}.hash")
                    self.assertEqual(
                        archive_hash.read_text(),
                        command.calculate_file_hash(str(archive)),
                    )
            finally:
                os.chdir(previous_cwd)

    def test_multi_arch_archives_have_flat_isolated_site_packages(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "plugin"
            source.mkdir()
            (source / "__main__.py").write_text(
                "print('ok')\n", encoding="utf-8"
            )
            (source / "plugin.toml").write_text(
                _manifest_v2(),
                encoding="utf-8",
            )
            stale_site_packages = source / "site-packages"
            stale_site_packages.mkdir()
            (stale_site_packages / "stale.txt").write_text(
                "stale\n", encoding="utf-8"
            )

            def build_install_command(**kwargs: object) -> list[str]:
                return [
                    "mock-install",
                    str(kwargs["arch"]),
                    str(kwargs["site_packages_dir"]),
                ]

            def install(
                args: list[str], **_kwargs: object
            ) -> subprocess.CompletedProcess[bytes]:
                target = Path(args[2])
                target.mkdir(parents=True, exist_ok=True)
                (target / "fixture.txt").write_text(
                    args[1], encoding="utf-8"
                )
                return subprocess.CompletedProcess(args, 0, b"", b"")

            previous_cwd = Path.cwd()
            try:
                os.chdir(root)
                command = PackageCommand()
                command._console = Console(file=StringIO(), force_terminal=False)
                with (
                    patch.object(
                        command,
                        "_build_install_command",
                        side_effect=build_install_command,
                    ) as build_command,
                    patch(
                        "tools.package_command.subprocess.run",
                        side_effect=install,
                    ),
                ):
                    command.run(
                        source_dir=str(source),
                        platform="Android",
                        arch=["arm64-v8a", "x86_64"],
                        requirements=["fixture-package"],
                        asset="build/plugin.pyrix",
                        exclude=[],
                        cleanup_app_files=[],
                        cleanup_package_files=[],
                    )

                self.assertFalse((root / "build" / "plugin.pyrix").exists())
                self.assertEqual(
                    [call.kwargs["arch"] for call in build_command.call_args_list],
                    ["arm64-v8a", "x86_64"],
                )
                for architecture in ("arm64-v8a", "x86_64"):
                    archive = (
                        root
                        / "build"
                        / f"fixture-plugin-Android-{architecture}.pyrix"
                    )
                    archive_hash = Path(f"{archive}.hash")
                    self.assertTrue(archive.is_file())
                    self.assertEqual(
                        archive_hash.read_text(encoding="ascii"),
                        command.calculate_file_hash(str(archive)),
                    )
                    with zipfile.ZipFile(archive) as package:
                        names = package.namelist()
                        self.assertEqual(
                            package.read("site-packages/fixture.txt").decode(),
                            architecture,
                        )
                        self.assertNotIn("site-packages/stale.txt", names)
                        self.assertFalse(
                            any(
                                name.startswith(
                                    f"site-packages/{candidate}/"
                                )
                                for candidate in platforms["Android"]
                                for name in names
                            )
                        )
                        metadata = json.loads(
                            package.read(runtime_metadata_filename).decode()
                        )
                        self.assertEqual(
                            metadata["target"],
                            {
                                "platform": "Android",
                                "architectures": [architecture],
                            },
                        )
            finally:
                os.chdir(previous_cwd)

    def test_multi_arch_archives_are_split_without_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "plugin"
            source.mkdir()
            (source / "__main__.py").write_text(
                "print('ok')\n", encoding="utf-8"
            )
            (source / "plugin.toml").write_text(
                _manifest_v2(),
                encoding="utf-8",
            )
            legacy_arch_dirs = [
                source / "site-packages" / architecture
                for architecture in platforms["Android"]
            ]
            for legacy_arch_dir in legacy_arch_dirs:
                legacy_arch_dir.mkdir(parents=True)
                (legacy_arch_dir / "legacy.txt").write_text(
                    legacy_arch_dir.name, encoding="utf-8"
                )

            previous_cwd = Path.cwd()
            try:
                os.chdir(root)
                command = PackageCommand()
                command._console = Console(file=StringIO(), force_terminal=False)
                command.run(
                    source_dir=str(source),
                    platform="Android",
                    arch=[],
                    requirements=[],
                    asset="build/plugin.pyrix",
                    exclude=[],
                    skip_site_packages=True,
                    cleanup_app_files=[],
                    cleanup_package_files=[],
                )

                self.assertFalse((root / "build" / "plugin.pyrix").exists())
                for architecture in platforms["Android"]:
                    archive = (
                        root
                        / "build"
                        / f"fixture-plugin-Android-{architecture}.pyrix"
                    )
                    self.assertTrue(archive.is_file())
                    self.assertTrue(Path(f"{archive}.hash").is_file())
                    with zipfile.ZipFile(archive) as package:
                        names = package.namelist()
                        self.assertEqual(
                            package.read("site-packages/legacy.txt").decode(),
                            architecture,
                        )
                        self.assertFalse(
                            any(
                                name.startswith(
                                    f"site-packages/{candidate}/"
                                )
                                for candidate in platforms["Android"]
                                for name in names
                            )
                        )
                        metadata = json.loads(
                            package.read(runtime_metadata_filename).decode()
                        )
                        self.assertEqual(
                            metadata["target"]["architectures"],
                            [architecture],
                        )
            finally:
                os.chdir(previous_cwd)

    def test_source_dot_does_not_embed_build_or_archive_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "__main__.py").write_text(
                "print('ok')\n", encoding="utf-8"
            )
            (root / "plugin.toml").write_text(
                _manifest_v2(),
                encoding="utf-8",
            )
            build_dir = root / "build"
            runtime_cache = build_dir / "build_python_fixture" / "python"
            runtime_cache.mkdir(parents=True)
            (runtime_cache / "python.exe").write_text(
                "runtime", encoding="utf-8"
            )
            output_dir = root / "dist"
            output_dir.mkdir()
            stale_archive = output_dir / "fixture-plugin-Linux.pyrix"
            stale_archive.write_text("stale", encoding="utf-8")

            previous_cwd = Path.cwd()
            try:
                os.chdir(root)
                command = PackageCommand()
                command._console = Console(file=StringIO(), force_terminal=False)
                command.run(
                    source_dir=".",
                    platform="Android",
                    arch=["arm64-v8a"],
                    requirements=[],
                    asset="dist/plugin.pyrix",
                    exclude=[],
                    skip_site_packages=True,
                    cleanup_app_files=[],
                    cleanup_package_files=[],
                )

                archive = output_dir / "fixture-plugin-Android-arm64-v8a.pyrix"
                with zipfile.ZipFile(archive) as package:
                    self.assertFalse(
                        any(
                            name == "build"
                            or name.startswith(("build/", "dist/fixture-plugin"))
                            for name in package.namelist()
                        )
                    )
                self.assertTrue(stale_archive.exists())
            finally:
                os.chdir(previous_cwd)

    def test_native_staging_clears_dependencies_when_requirements_are_empty(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "plugin"
            source.mkdir()
            (source / "__main__.py").write_text(
                "print('ok')\n", encoding="utf-8"
            )
            (source / "plugin.toml").write_text(
                _manifest_v2(),
                encoding="utf-8",
            )
            staging = root / "staged-app"
            site_packages = root / "site-packages"
            stale = site_packages / "arm64-v8a" / "stale.txt"
            stale.parent.mkdir(parents=True)
            stale.write_text("stale\n", encoding="utf-8")

            previous_cwd = Path.cwd()
            try:
                os.chdir(root)
                with patch.dict(
                    os.environ,
                    {
                        app_environment_var: str(staging),
                        site_packages_env_var: str(site_packages),
                    },
                    clear=False,
                ):
                    command = PackageCommand()
                    command._console = Console(
                        file=StringIO(), force_terminal=False
                    )
                    command.run(
                        source_dir=str(source),
                        platform="Android",
                        arch=["arm64-v8a"],
                        requirements=[],
                        exclude=[],
                        cleanup_app_files=[],
                        cleanup_package_files=[],
                    )

                self.assertFalse(stale.exists())
                self.assertTrue((staging / "__main__.py").is_file())
            finally:
                os.chdir(previous_cwd)

    def test_successful_archive_publish_removes_stale_architecture_outputs(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "plugin"
            source.mkdir()
            (source / "__main__.py").write_text(
                "print('ok')\n", encoding="utf-8"
            )
            (source / "plugin.toml").write_text(
                _manifest_v2(),
                encoding="utf-8",
            )
            output_dir = root / "build"
            output_dir.mkdir()
            for name in (
                "fixture-plugin.pyrix",
                "fixture-plugin-Android-x86_64.pyrix",
                "fixture-plugin-Android-armeabi-v7a.pyrix",
            ):
                archive = output_dir / name
                archive.write_text("stale", encoding="utf-8")
                Path(f"{archive}.hash").write_text(
                    "stale", encoding="utf-8"
                )

            previous_cwd = Path.cwd()
            try:
                os.chdir(root)
                command = PackageCommand()
                command._console = Console(file=StringIO(), force_terminal=False)
                command.run(
                    source_dir=str(source),
                    platform="Android",
                    arch=["arm64-v8a"],
                    requirements=[],
                    asset="build/plugin.pyrix",
                    exclude=[],
                    skip_site_packages=True,
                    cleanup_app_files=[],
                    cleanup_package_files=[],
                )

                current = output_dir / "fixture-plugin-Android-arm64-v8a.pyrix"
                self.assertTrue(current.is_file())
                self.assertTrue(Path(f"{current}.hash").is_file())
                for stale_name in (
                    "fixture-plugin.pyrix",
                    "fixture-plugin-Android-x86_64.pyrix",
                    "fixture-plugin-Android-armeabi-v7a.pyrix",
                ):
                    stale_archive = output_dir / stale_name
                    self.assertFalse(stale_archive.exists())
                    self.assertFalse(Path(f"{stale_archive}.hash").exists())
            finally:
                os.chdir(previous_cwd)

    def test_platform_archives_coexist_across_sequential_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "plugin"
            source.mkdir()
            (source / "__main__.py").write_text(
                "print('ok')\n", encoding="utf-8"
            )
            (source / "plugin.toml").write_text(
                _manifest_v2(),
                encoding="utf-8",
            )

            previous_cwd = Path.cwd()
            try:
                os.chdir(root)
                command = PackageCommand()
                command._console = Console(file=StringIO(), force_terminal=False)
                for target_platform, target_architectures in (
                    ("Android", ["arm64-v8a"]),
                    ("Darwin", ["arm64"]),
                    ("Windows", []),
                    ("Linux", []),
                ):
                    command.run(
                        source_dir=str(source),
                        platform=target_platform,
                        arch=target_architectures,
                        requirements=[],
                        asset="build/custom-output.pyrix",
                        exclude=[],
                        skip_site_packages=True,
                        cleanup_app_files=[],
                        cleanup_package_files=[],
                    )

                expected = {
                    "fixture-plugin-Android-arm64-v8a.pyrix",
                    "fixture-plugin-Darwin-arm64.pyrix",
                    "fixture-plugin-Windows.pyrix",
                    "fixture-plugin-Linux.pyrix",
                }
                for name in expected:
                    archive = root / "build" / name
                    self.assertTrue(archive.is_file(), name)
                    self.assertTrue(Path(f"{archive}.hash").is_file(), name)
                self.assertFalse((root / "build" / "custom-output.pyrix").exists())
            finally:
                os.chdir(previous_cwd)

    def test_explicit_asset_still_requires_manifest_plugin_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "plugin"
            source.mkdir()
            (source / "__main__.py").write_text(
                "print('ok')\n", encoding="utf-8"
            )

            valid_manifest = _manifest_v2()
            for manifest in (
                valid_manifest.replace('id = "fixture-plugin"\n', ""),
                valid_manifest.replace(
                    'id = "fixture-plugin"',
                    'id = ""',
                ),
                valid_manifest.replace(
                    'id = "fixture-plugin"',
                    "id = 1",
                ),
            ):
                with self.subTest(manifest=manifest):
                    (source / "plugin.toml").write_text(
                        manifest,
                        encoding="utf-8",
                    )
                    command = PackageCommand()
                    command._console = Console(
                        file=StringIO(), force_terminal=False
                    )
                    with self.assertRaisesRegex(
                        ValueError,
                        PluginManifestErrorCode.INVALID_SCHEMA,
                    ):
                        command.run(
                            source_dir=str(source),
                            platform="Windows",
                            arch=[],
                            requirements=[],
                            asset="custom/output.pyrix",
                            exclude=[],
                            skip_site_packages=True,
                            cleanup_app_files=[],
                            cleanup_package_files=[],
                        )

    def test_failed_multi_arch_build_does_not_publish_partial_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "plugin"
            source.mkdir()
            (source / "__main__.py").write_text(
                "print('ok')\n", encoding="utf-8"
            )
            (source / "plugin.toml").write_text(
                _manifest_v2(),
                encoding="utf-8",
            )

            previous_cwd = Path.cwd()
            try:
                os.chdir(root)
                command = PackageCommand()
                command._console = Console(file=StringIO(), force_terminal=False)
                create_archive = command._create_archive

                def fail_second_archive(
                    source_dir: Path,
                    destination: Path,
                    *,
                    reported_destination: Path | None = None,
                ) -> None:
                    if reported_destination is not None and (
                        reported_destination.name
                        == "fixture-plugin-Android-x86_64.pyrix"
                    ):
                        raise RuntimeError("simulated archive failure")
                    create_archive(
                        source_dir,
                        destination,
                        reported_destination=reported_destination,
                    )

                with patch.object(
                    command,
                    "_create_archive",
                    side_effect=fail_second_archive,
                ):
                    with self.assertRaisesRegex(
                        RuntimeError, "simulated archive failure"
                    ):
                        command.run(
                            source_dir=str(source),
                            platform="Android",
                            arch=["arm64-v8a", "x86_64"],
                            requirements=[],
                            asset="build/plugin.pyrix",
                            exclude=[],
                            skip_site_packages=True,
                            cleanup_app_files=[],
                            cleanup_package_files=[],
                        )

                self.assertFalse(
                    (
                        root
                        / "build"
                        / "fixture-plugin-Android-arm64-v8a.pyrix"
                    ).exists()
                )
                self.assertFalse(
                    (
                        root
                        / "build"
                        / "fixture-plugin-Android-x86_64.pyrix"
                    ).exists()
                )
            finally:
                os.chdir(previous_cwd)

    def test_failed_archive_publication_restores_previous_family(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "plugin"
            source.mkdir()
            (source / "__main__.py").write_text(
                "print('new')\n", encoding="utf-8"
            )
            (source / "plugin.toml").write_text(
                _manifest_v2(),
                encoding="utf-8",
            )
            output_dir = root / "build"
            output_dir.mkdir()
            previous_archives: dict[Path, tuple[bytes, str]] = {}
            for architecture in ("arm64-v8a", "x86_64"):
                archive = (
                    output_dir / f"fixture-plugin-Android-{architecture}.pyrix"
                )
                archive.write_bytes(f"old-{architecture}".encode())
                archive_hash = hashlib.md5(archive.read_bytes()).hexdigest()
                Path(f"{archive}.hash").write_text(
                    archive_hash, encoding="ascii"
                )
                previous_archives[archive] = (archive.read_bytes(), archive_hash)

            real_replace = os.replace
            failed = False

            def fail_first_published_hash(
                source_path: str | Path,
                destination_path: str | Path,
            ) -> None:
                nonlocal failed
                destination = Path(destination_path)
                if (
                    not failed
                    and destination.name
                    == "fixture-plugin-Android-arm64-v8a.pyrix.hash"
                ):
                    failed = True
                    raise OSError("simulated hash publication failure")
                real_replace(source_path, destination_path)

            previous_cwd = Path.cwd()
            try:
                os.chdir(root)
                command = PackageCommand()
                command._console = Console(file=StringIO(), force_terminal=False)
                with patch(
                    "tools.package_command.os.replace",
                    side_effect=fail_first_published_hash,
                ):
                    with self.assertRaisesRegex(
                        OSError, "simulated hash publication failure"
                    ):
                        command.run(
                            source_dir=str(source),
                            platform="Android",
                            arch=["arm64-v8a", "x86_64"],
                            requirements=[],
                            asset="build/plugin.pyrix",
                            exclude=[],
                            skip_site_packages=True,
                            cleanup_app_files=[],
                            cleanup_package_files=[],
                        )

                self.assertTrue(failed)
                for archive, (contents, archive_hash) in previous_archives.items():
                    self.assertEqual(archive.read_bytes(), contents)
                    self.assertEqual(
                        Path(f"{archive}.hash").read_text(encoding="ascii"),
                        archive_hash,
                    )
            finally:
                os.chdir(previous_cwd)

    def test_archive_publication_rejects_directory_family_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            destination = root / "plugin.pyrix"
            staged = root / "staged.pyrix"
            staged.write_bytes(b"new archive")
            Path(f"{staged}.hash").write_text("new hash", encoding="ascii")

            conflicting_directory = root / "plugin-arm64-v8a.pyrix"
            conflicting_directory.mkdir()
            with self.assertRaisesRegex(
                ValueError, "is not a regular file"
            ):
                PackageCommand._publish_archive_family(
                    destination,
                    [(staged, conflicting_directory)],
                )

            self.assertTrue(conflicting_directory.is_dir())
            self.assertEqual(staged.read_bytes(), b"new archive")
            self.assertEqual(
                Path(f"{staged}.hash").read_text(encoding="ascii"),
                "new hash",
            )

    def test_archive_publication_rejects_dangling_symlink_family_paths(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            destination = root / "plugin.pyrix"
            staged = root / "staged.pyrix"
            staged.write_bytes(b"new archive")
            Path(f"{staged}.hash").write_text("new hash", encoding="ascii")
            linked_output = root / "plugin-arm64-v8a.pyrix"
            try:
                linked_output.symlink_to(root / "missing.pyrix")
            except OSError as error:
                self.skipTest(f"Symbolic links are unavailable: {error}")

            with self.assertRaisesRegex(
                ValueError, "is not a regular file"
            ):
                PackageCommand._publish_archive_family(
                    destination,
                    [(staged, linked_output)],
                )

            self.assertTrue(linked_output.is_symlink())
            self.assertEqual(staged.read_bytes(), b"new archive")

    def test_archive_publication_rejects_valid_symlink_family_paths(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            destination = root / "plugin.pyrix"
            staged = root / "staged.pyrix"
            staged.write_bytes(b"new archive")
            Path(f"{staged}.hash").write_text("new hash", encoding="ascii")
            linked_target = root / "existing.pyrix"
            linked_target.write_bytes(b"linked archive")
            linked_output = root / "plugin-arm64-v8a.pyrix"
            try:
                linked_output.symlink_to(linked_target)
            except OSError as error:
                self.skipTest(f"Symbolic links are unavailable: {error}")

            with self.assertRaisesRegex(
                ValueError, "is not a regular file"
            ):
                PackageCommand._publish_archive_family(
                    destination,
                    [(staged, linked_output)],
                )

            self.assertTrue(linked_output.is_symlink())
            self.assertEqual(linked_target.read_bytes(), b"linked archive")
            self.assertEqual(staged.read_bytes(), b"new archive")

    def test_archive_backup_cleanup_does_not_change_publication_result(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            destination = root / "plugin.pyrix"
            published = root / "plugin-arm64-v8a.pyrix"
            published.write_bytes(b"old archive")
            Path(f"{published}.hash").write_text("old hash", encoding="ascii")
            staged = root / "staged.pyrix"
            staged.write_bytes(b"new archive")
            Path(f"{staged}.hash").write_text("new hash", encoding="ascii")

            real_rmtree = shutil.rmtree

            def fail_backup_cleanup(
                target: str | Path,
                *args: object,
                **kwargs: object,
            ) -> None:
                if Path(target).name.startswith(
                    "pyrite_plugin_archive_backup"
                ):
                    raise OSError("simulated backup cleanup failure")
                real_rmtree(target, *args, **kwargs)

            with patch(
                "tools.package_command.shutil.rmtree",
                side_effect=fail_backup_cleanup,
            ):
                PackageCommand._publish_archive_family(
                    destination,
                    [(staged, published)],
                )

            self.assertEqual(published.read_bytes(), b"new archive")
            self.assertEqual(
                Path(f"{published}.hash").read_text(encoding="ascii"),
                "new hash",
            )

    def test_archive_backup_cleanup_does_not_hide_publication_failure(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            destination = root / "plugin.pyrix"
            published = root / "plugin-arm64-v8a.pyrix"
            published.write_bytes(b"old archive")
            Path(f"{published}.hash").write_text("old hash", encoding="ascii")
            staged = root / "staged.pyrix"
            staged.write_bytes(b"new archive")
            Path(f"{staged}.hash").write_text("new hash", encoding="ascii")

            real_replace = os.replace

            def fail_published_hash(
                source_path: str | Path,
                destination_path: str | Path,
            ) -> None:
                if Path(destination_path) == Path(f"{published}.hash"):
                    raise OSError("simulated publication failure")
                real_replace(source_path, destination_path)

            with (
                patch(
                    "tools.package_command.os.replace",
                    side_effect=fail_published_hash,
                ),
                patch(
                    "tools.package_command.shutil.rmtree",
                    side_effect=RuntimeError("simulated cleanup failure"),
                ),
            ):
                with self.assertRaisesRegex(
                    OSError, "simulated publication failure"
                ):
                    PackageCommand._publish_archive_family(
                        destination,
                        [(staged, published)],
                    )

            self.assertEqual(published.read_bytes(), b"old archive")
            self.assertEqual(
                Path(f"{published}.hash").read_text(encoding="ascii"),
                "old hash",
            )

    def test_darwin_archives_do_not_merge_site_packages(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "plugin"
            source.mkdir()
            (source / "__main__.py").write_text(
                "print('ok')\n", encoding="utf-8"
            )
            (source / "plugin.toml").write_text(
                _manifest_v2(),
                encoding="utf-8",
            )

            previous_cwd = Path.cwd()
            try:
                os.chdir(root)
                command = PackageCommand()
                command._console = Console(file=StringIO(), force_terminal=False)
                with (
                    patch.object(
                        command,
                        "_install_arch_dependencies",
                        return_value=False,
                    ),
                    patch(
                        "tools.package_command.macos_utils."
                        "merge_macos_site_packages"
                    ) as merge,
                ):
                    command.run(
                        source_dir=str(source),
                        platform="Darwin",
                        arch=["arm64", "x86_64"],
                        requirements=["fixture-package"],
                        asset="build/plugin.pyrix",
                        exclude=[],
                        cleanup_app_files=[],
                        cleanup_package_files=[],
                    )

                merge.assert_not_called()
                self.assertTrue(
                    (
                        root / "build" / "fixture-plugin-Darwin-arm64.pyrix"
                    ).is_file()
                )
                self.assertTrue(
                    (
                        root / "build" / "fixture-plugin-Darwin-x86_64.pyrix"
                    ).is_file()
                )
            finally:
                os.chdir(previous_cwd)

    def test_manifest_python_version_is_validated(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "plugin"
            source.mkdir()
            (source / "__main__.py").write_text("print('ok')\n", encoding="utf-8")
            cases = [
                (
                    _manifest_v2(python_version="3.11"),
                    "Unknown Python version: 3.11",
                ),
                (
                    _manifest_v2(extra="python_version = 3.14\n"),
                    PluginManifestErrorCode.INVALID_SCHEMA,
                ),
            ]
            for manifest, error in cases:
                with self.subTest(error=error):
                    (source / "plugin.toml").write_text(
                        manifest,
                        encoding="utf-8",
                    )
                    command = PackageCommand()
                    command._console = Console(file=StringIO(), force_terminal=False)

                    with self.assertRaisesRegex(ValueError, error):
                        command.run(
                            source_dir=str(source),
                            platform="Windows",
                            arch=[],
                            requirements=[],
                            exclude=[],
                            cleanup_app_files=[],
                            cleanup_package_files=[],
                        )

    def test_compile_app_keeps_a_compiled_plugin_entry_point(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "plugin"
            source.mkdir()
            (source / "__main__.py").write_text("print('ok')\n", encoding="utf-8")
            (source / "plugin.toml").write_text(
                _manifest_v2(),
                encoding="utf-8",
            )
            archive_base = root / "build" / "compiled.pyrix"
            archive = root / "build" / "fixture-plugin-Windows.pyrix"

            previous_cwd = Path.cwd()
            try:
                os.chdir(root)
                command = PackageCommand()
                command._console = Console(file=StringIO(), force_terminal=False)
                with patch.object(
                    command,
                    "_target_python",
                    return_value=Path(sys.executable),
                ):
                    command.run(
                        source_dir=str(source),
                        platform="Windows",
                        arch=[],
                        requirements=[],
                        asset=str(archive_base.relative_to(root)),
                        exclude=[],
                        skip_site_packages=True,
                        compile_app=True,
                        cleanup_app_files=[],
                        cleanup_package_files=[],
                    )

                with zipfile.ZipFile(archive) as package:
                    self.assertIn("__main__.pyc", package.namelist())
                    self.assertNotIn("__main__.py", package.namelist())
            finally:
                os.chdir(previous_cwd)

    def test_required_plugin_files_cannot_be_removed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "plugin"
            source.mkdir()
            (source / "__main__.py").write_text("print('ok')\n", encoding="utf-8")
            (source / "plugin.toml").write_text(
                _manifest_v2(),
                encoding="utf-8",
            )
            cases = [
                (
                    "plugin.toml",
                    {"exclude": ["plugin.toml"]},
                ),
                (
                    "__main__.py",
                    {
                        "exclude": [],
                        "cleanup_app": True,
                        "cleanup_app_files": ["**/__main__.py"],
                    },
                ),
            ]

            previous_cwd = Path.cwd()
            try:
                os.chdir(root)
                for required_file, overrides in cases:
                    with self.subTest(required_file=required_file):
                        command = PackageCommand()
                        command._console = Console(
                            file=StringIO(), force_terminal=False
                        )
                        kwargs = {
                            "source_dir": str(source),
                            "platform": "Windows",
                            "arch": [],
                            "requirements": [],
                            "asset": f"build/missing-{required_file}.pyrix",
                            "exclude": [],
                            "skip_site_packages": True,
                            "cleanup_app_files": [],
                            "cleanup_package_files": [],
                            **overrides,
                        }
                        with self.assertRaisesRegex(
                            ValueError, required_file.replace(".", r"\.")
                        ):
                            command.run(**kwargs)
            finally:
                os.chdir(previous_cwd)


if __name__ == "__main__":
    unittest.main()
