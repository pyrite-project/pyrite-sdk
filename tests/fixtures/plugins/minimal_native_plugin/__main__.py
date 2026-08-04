from pyrite_sdk.core.plugin import UiPlugin


class MinimalNativePlugin(UiPlugin):
    def on_start(self) -> None:
        pass


plugin = MinimalNativePlugin()
