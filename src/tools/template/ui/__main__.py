from pyrite_sdk.api.ui.page import Page
from pyrite_sdk.api.ui.sentence import *
from pyrite_sdk.api.ui.widgets import *
from pyrite_sdk.core.plugin import UiPlugin
from pyrite_sdk.models.consts import Package, Ui

class TemplateUiPlugin(UiPlugin):
    def __init__(self):
        super().__init__()

        home_page = Page([Package.core.widgets, Package.core.material])
        root_widget = NewWidget(Ui.root).add_to(home_page)
        Text("Hello World").add_to(root_widget)
        
        self.pages["home"] = home_page

    def on_start(self):
        print("Template Ui Plugin started")

    def on_dispose(self):
        print("Template Ui Plugin disposed")


plugin = TemplateUiPlugin()

if __name__ == "__main__":
    plugin.start()
