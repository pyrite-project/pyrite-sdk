from pyrite_sdk.api.components import *
from pyrite_sdk.core.plugin import UiPlugin


class <PluginId>Plugin(UiPlugin):
    def __init__(self) -> None:
        super().__init__()
        self.main_view = self.views.create("<plugin-id>.main")
        self.main_view.snapshot([
            Text("Hello world!"),
        ])

    def on_start(self) -> None:
        print("<PluginId> Plugin started")
        self.main_view.open()

    def on_dispose(self) -> None:
        print("<PluginId> Plugin disposed")


plugin = <PluginId>Plugin()

if __name__ == "__main__":
    plugin.start()
