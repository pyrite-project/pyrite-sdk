import importlib.util
import sys
from pathlib import Path
from unittest.mock import Mock, patch

from pyrite_sdk.core.context import PluginContext
from rich.console import Console


class TestCommand:
    def _load_module(self, source_path: Path) -> None:
        spec = importlib.util.spec_from_file_location(
            "plugin",
            source_path / "__main__.py",
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load plugin from {source_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules["plugin"] = module
        context = PluginContext.standalone(source_path)
        with (
            patch(
                "pyrite_sdk.core.bridge.DartBridgeTransport.from_environment",
                return_value=Mock(),
            ),
            patch(
                "pyrite_sdk.core.bridge.PluginContext.from_environment",
                return_value=context,
            ),
            patch("pyrite_sdk.core.bridge.Bridge.start", lambda self: None),
        ):
            spec.loader.exec_module(module)
        self.plugin = module

    def check_completeness(self, source_path: Path) -> bool:
        print("Checking completeness...")
        required_files = ["__main__.py", "plugin.toml", "requirements.txt"]
        missing = [
            source_path / name
            for name in required_files
            if not (source_path / name).exists()
        ]
        for path in missing:
            print("Missing file:", path)
        return bool(missing)

    def run(self, source_path: Path, raw_output: bool, console: Console) -> None:
        if self.check_completeness(source_path):
            if raw_output:
                print("Required files are missing.")
            else:
                console.print("[red]Required files are missing.[/red]")
            return
        self._load_module(source_path)
        if raw_output:
            print("Completeness check passed.")
        else:
            console.print("[green]Completeness check passed.[/green]")
