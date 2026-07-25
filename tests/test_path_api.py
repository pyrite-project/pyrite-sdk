import os
import unittest
from pathlib import Path as FilePath
from unittest.mock import patch

from pyrite_sdk.api.path import Path


class _Bridge:
    def request_path(self, scope):
        return FilePath("host") / scope.value


class PathApiTest(unittest.TestCase):
    def test_plugin_paths_are_captured_per_instance(self) -> None:
        first_environment = {
            "PYRITE_IDE_PLUGIN_DIR": "first/plugin",
            "PYRITE_IDE_PLUGIN_DATA_DIR": "first/data",
            "PYRITE_IDE_PLUGIN_CACHE_DIR": "first/cache",
            "PYRITE_IDE_PLUGIN_TEMP_DIR": "first/temp",
        }
        second_environment = {
            key: value.replace("first", "second")
            for key, value in first_environment.items()
        }

        with patch.dict(os.environ, first_environment, clear=False):
            first = Path(_Bridge())  # type: ignore[arg-type]
        with patch.dict(os.environ, second_environment, clear=False):
            second = Path(_Bridge())  # type: ignore[arg-type]
            self.assertEqual(first.plugin(), FilePath("first/plugin"))
            self.assertEqual(first.data(), FilePath("first/data"))
            self.assertEqual(first.cache(), FilePath("first/cache"))
            self.assertEqual(first.temp(), FilePath("first/temp"))

        self.assertEqual(second.plugin(), FilePath("second/plugin"))
        self.assertEqual(second.data(), FilePath("second/data"))


if __name__ == "__main__":
    unittest.main()
