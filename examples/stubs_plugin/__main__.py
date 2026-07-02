from pyrite_sdk.core.plugin import DataPlugin


class MicroPythonStubsPlugin(DataPlugin):
    def on_contribute(self):
        provider_id = "micropython-stubs-example"
        root = self.path.plugin() / "stubs"
        self.stubs.contribute(
            provider_id=provider_id,
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
        self.settings.micropython_stubs.get_layers(
            lambda **response: self._configure_default_layers(
                provider_id,
                response.get("data", {}).get("value", []),
            )
        )

    def _configure_default_layers(self, provider_id, current_layers):
        if current_layers:
            self.message.warning("已检测到现有 Stubs Layers，未覆盖用户配置")
            return
        self.settings.micropython_stubs.set_enabled(True)
        self.settings.micropython_stubs.set_layers(
            [
                {"provider": provider_id, "profile": "generic"},
                {"provider": provider_id, "profile": "esp32"},
            ]
        )
        self.message.success("MicroPython Stubs Layers 已配置")


plugin = MicroPythonStubsPlugin()
plugin.run_once()
