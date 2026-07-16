import importlib.util
import os
import unittest
from pathlib import Path


EXAMPLE_DIR = Path(__file__).resolve().parents[1] / "examples" / "ui_plugin"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def load_example_module(example_dir: Path = EXAMPLE_DIR):
    module_path = example_dir / "__main__.py"
    spec = importlib.util.spec_from_file_location("ui_components_example", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class UiComponentsExampleTest(unittest.TestCase):
    def test_example_serializes_all_new_components_and_local_sources(self) -> None:
        example_dir = Path(os.environ.get("PYRITE_UI_EXAMPLE_DIR", EXAMPLE_DIR))
        module = load_example_module(example_dir)
        page = module.build_home_page(example_dir / "assets")
        rfw = page.to_rfw()

        for widget_name in (
            "Image",
            "VideoPlayer",
            "Tooltip",
            "Chip",
            "ExpansionTile",
            "DropdownButton",
        ):
            with self.subTest(widget=widget_name):
                self.assertIn(widget_name, rfw)

        self.assertIn('sourceType: "file"', rfw)
        self.assertIn("preview.png", rfw)
        self.assertIn("demo.mp4", rfw)
        self.assertIn('DropdownButton(items: [{"value": "contain"', rfw)

        preview = example_dir / "assets" / "preview.png"
        video = example_dir / "assets" / "demo.mp4"
        self.assertGreater(preview.stat().st_size, len(PNG_SIGNATURE))
        self.assertGreater(video.stat().st_size, 12)
        self.assertEqual(preview.read_bytes()[: len(PNG_SIGNATURE)], PNG_SIGNATURE)
        self.assertEqual(video.read_bytes()[4:8], b"ftyp")


if __name__ == "__main__":
    unittest.main()
