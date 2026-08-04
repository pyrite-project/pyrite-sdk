import tempfile
import unittest
from pathlib import Path as FilePath

from pyrite_sdk.api.path import Path
from pyrite_sdk.core.context import PluginContext
from pyrite_sdk.models.consts import PathScope


class _Bridge:
    def __init__(self, context=None):
        self.context = context
        self.path_requests = []
        self.pushed = []

    def request_path(self, scope):
        self.path_requests.append(scope)
        return FilePath("host") / scope.value

    def push_wait_response(self, envelope, callback=None):
        self.pushed.append((envelope, callback))


class PathApiTest(unittest.TestCase):
    def test_plugin_paths_come_from_captured_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = FilePath(temp).resolve()
            context = PluginContext(
                id="path-plugin",
                session_id="path-session",
                generation=2,
                plugin_dir=root / "plugin",
                data_dir=root / "data",
                cache_dir=root / "cache",
                temp_dir=root / "temp",
                capabilities=frozenset({"sdk.v1"}),
            )
            bridge = _Bridge(context)
            paths = Path(bridge)  # type: ignore[arg-type]

            self.assertEqual(paths.plugin(), root / "plugin")
            self.assertEqual(paths.data(), root / "data")
            self.assertEqual(paths.cache(), root / "cache")
            self.assertEqual(paths.temp(), root / "temp")
            self.assertEqual(bridge.path_requests, [])

    def test_missing_captured_path_falls_back_to_host_request(self) -> None:
        bridge = _Bridge()
        paths = Path(bridge)  # type: ignore[arg-type]

        self.assertEqual(paths.plugin(), FilePath("host/plugin"))
        self.assertEqual(paths.data(), FilePath("host/data"))
        self.assertEqual(paths.cache(), FilePath("host/cache"))
        self.assertEqual(paths.temp(), FilePath("host/temp"))
        self.assertEqual(
            bridge.path_requests,
            [
                PathScope.PLUGIN,
                PathScope.DATA,
                PathScope.CACHE,
                PathScope.TEMP,
            ],
        )

    def test_get_keeps_the_async_path_request_api(self) -> None:
        bridge = _Bridge()
        paths = Path(bridge)  # type: ignore[arg-type]
        callback = lambda **_: None

        paths.get(PathScope.DATA, callback)

        envelope, captured_callback = bridge.pushed[0]
        self.assertEqual(envelope.type, "sdk.path.request")
        self.assertEqual(envelope.payload, {"scope": PathScope.DATA})
        self.assertIs(captured_callback, callback)


if __name__ == "__main__":
    unittest.main()
