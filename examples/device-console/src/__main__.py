from pyrite_sdk.api.native_views import FormField
from pyrite_sdk.core.plugin import UiPlugin


class TemplateUiPlugin(UiPlugin):
    def __init__(self):
        super().__init__()
        self.main_view = self.views.form(
            "template-ui-plugin.main",
            title="Template",
        )
        self.main_view.set_items(
            [FormField(id="message", label="Message", value="Hello World")]
        )

    def on_start(self):
        print("Template UI Plugin started")
        self.main_view.open()

    def on_dispose(self):
        print("Template UI Plugin disposed")


plugin = TemplateUiPlugin()

if __name__ == "__main__":
    plugin.start()
