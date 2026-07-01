from pyrite_sdk.core.plugin import DataPlugin


class MicroPythonStubsPlugin(DataPlugin):
    def on_contribute(self):
        root = self.path.plugin() / "stubs"
        self.stubs.contribute(
            provider_id="micropython-stubs-example",
            kind="micropython",
            version="1.0.0",
            profiles=[
                {
                    "id": "generic",
                    "label": "MicroPython Generic Example",
                    "path": str(root / "generic"),
                    "priority": 10,
                },
                {
                    "id": "esp32",
                    "label": "MicroPython ESP32 Example",
                    "path": str(root / "esp32"),
                    "priority": 20,
                },
            ],
            aliases=["micropython", "example"],
        )


plugin = MicroPythonStubsPlugin()
plugin.run_once()
