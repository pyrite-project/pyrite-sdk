import unittest
from unittest.mock import patch

from typer.testing import CliRunner

from tools.main import app, _build_requirements


class PackagerCliTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
