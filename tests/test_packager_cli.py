import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pyrite_sdk.models.manifest import PluginType, load_file
from typer.testing import CliRunner

from tools.main import app, _build_requirements


class PackagerCliTest(unittest.TestCase):
    def test_create_generates_a_valid_manifest_v2_template(self) -> None:
        cases = {
            "ui": (PluginType.UI, ["ui.view"]),
            "service": (PluginType.SERVICE, ["file.read"]),
            "data": (PluginType.DATA, ["data.write"]),
        }
        for template, (plugin_type, permissions) in cases.items():
            with (
                self.subTest(template=template),
                tempfile.TemporaryDirectory() as temp,
            ):
                result = CliRunner().invoke(app, ["create", template, temp])

                self.assertEqual(result.exit_code, 0, result.output)
                manifest = load_file(Path(temp) / "src" / "plugin.toml")
                self.assertEqual(manifest.manifest_version, 2)
                self.assertEqual(manifest.type, plugin_type)
                self.assertEqual(manifest.permissions, permissions)

    def test_create_refuses_to_overwrite_existing_template_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "src"
            destination.mkdir()
            manifest = destination / "plugin.toml"
            manifest.write_text("keep me\n", encoding="utf-8")

            result = CliRunner().invoke(app, ["create", "ui", temp])

            self.assertNotEqual(result.exit_code, 0, result.output)
            self.assertIn("already contains template files", result.output)
            self.assertEqual(manifest.read_text(encoding="utf-8"), "keep me\n")
            self.assertFalse((destination / "__main__.py").exists())

    def test_requirements_file_expands_to_pip_requirements_args(self) -> None:
        self.assertEqual(
            _build_requirements(
                ["--find-links=dist"],
                "examples/ui_plugin/requirements.txt",
            ),
            ["-r", "examples/ui_plugin/requirements.txt", "--find-links=dist"],
        )

    def test_cli_accepts_requirements_file_short_option(self) -> None:
        runner = CliRunner()

        with patch("tools.main.PackageCommand") as package_command:
            result = runner.invoke(
                app,
                [
                    "package",
                    "examples/ui_plugin",
                    "-p",
                    "Darwin",
                    "-rf",
                    "examples/ui_plugin/requirements.txt",
                    "-r",
                    "--find-links=dist",
                    "--skip-site-packages",
                ],
            )

        self.assertEqual(result.exit_code, 0, result.output)
        package_command.return_value.run.assert_called_once()
        _, kwargs = package_command.return_value.run.call_args
        self.assertEqual(
            kwargs["requirements"],
            ["-r", "examples/ui_plugin/requirements.txt", "--find-links=dist"],
        )

    def test_cli_rejects_removed_python_version_option(self) -> None:
        result = CliRunner().invoke(
            app,
            [
                "package",
                "examples/ui_plugin",
                "-p",
                "Windows",
                "--python-version",
                "3.12",
                "--skip-site-packages",
            ],
        )

        self.assertEqual(result.exit_code, 2, result.output)
        self.assertIn("No such option", result.output)

    def test_cli_packages_all_platforms(self) -> None:
        runner = CliRunner()

        with patch("tools.main.PackageCommand") as package_command:
            result = runner.invoke(
                app,
                [
                    "package",
                    "examples/ui_plugin",
                    "--platform",
                    "all",
                    "--skip-site-packages",
                ],
            )

        self.assertEqual(result.exit_code, 0, result.output)
        calls = package_command.return_value.run.call_args_list
        self.assertEqual(
            [call.kwargs["platform"] for call in calls],
            ["Android", "Darwin", "Windows", "Linux"],
        )


if __name__ == "__main__":
    unittest.main()
