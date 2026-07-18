from rich.panel import Panel
import sys
import os
from rich.console import Console
from pathlib import Path
import importlib.util
from .utils.rfw_formatter import format_rfw

class TestCommand:
    def __init__(self):
        pass

    def check_completeness(self, source_path: Path):
        err = False
        print("Checking completeness...")
        required_files = [
            "__main__.py",
            "plugin.toml",
            "requirements.txt"
        ]
        for file_name in required_files:
            file = source_path/file_name
            if not (file).exists():
                err = True
                print("Missing file:", file)
        return err

    def _load_module(self, source_path: Path):
        os.environ["PYRITE_IDE_PLUGIN_PORT"] = "1225"
        spec = importlib.util.spec_from_file_location("plugin", source_path/"__main__.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules["plugin"] = module
        spec.loader.exec_module(module)
        self.plugin = module
        
    def get_rfw_text(
            self,
            source_path: Path,
            raw_output: bool,
            no_format_rfw: bool,
            console: Console
        ):
        if no_format_rfw:
            _format_rfw = lambda x:x
        else:
            _format_rfw = format_rfw
        self._load_module(source_path)
        print("\nRFW Text:")
        pages = self.plugin.plugin.pages
        if not raw_output:
            for p in pages:
                console.print(
                    Panel.fit(
                        _format_rfw(pages[p].to_rfw().rstrip("\n")),
                        title="page: "+p,
                        border_style="cyan"
                    )
                )
        else:
            for p in pages:
                print(f"-- page: {p} {'-'*20}")
                print(_format_rfw(pages[p].to_rfw().rstrip("\n")))

    def run(
            self,
            source_path: Path,
            rfw: bool,
            raw_output: bool,
            no_format_rfw: bool,
            console: Console
        ):
        completeness_err = self.check_completeness(source_path)
        if completeness_err:
            if not raw_output: console.print("[red]Required files are missing.[/red]")
            else: print("Required files are missing.")
            return
        else:
            if not raw_output: console.print("[green]Completeness check passed.[/green]")
            else: print("Completeness check passed.")
        if rfw:
            rfw_txt = self.get_rfw_text(
                source_path,
                raw_output,
                no_format_rfw,
                console
            )
