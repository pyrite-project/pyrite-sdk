from pyrite_sdk.api.components import *
from pyrite_sdk.core.plugin import UiPlugin


class TemplateUiPlugin(UiPlugin):
    def __init__(self) -> None:
        super().__init__()
        self.main_view = self.views.create("template-ui-plugin.main")
        self.main_view.snapshot([
            Text("Hello world!"),
        ])

    def on_start(self) -> None:
        print("Template UI Plugin started")
        self.main_view.open()

    def on_dispose(self) -> None:
        print("Template UI Plugin disposed")


plugin = TemplateUiPlugin()

if __name__ == "__main__":
    plugin.start()
