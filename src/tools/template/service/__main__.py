from pyrite_sdk.api.ui.sentence import *
from pyrite_sdk.api.ui.widgets import *
from pyrite_sdk.core.plugin import ServicePlugin

class TemplateServicePlugin(ServicePlugin):
    def __init__(self):
        super().__init__()

    def on_start(self):
        print("Template Service Plugin started")
        self.file.get_root_dir(
            lambda data: print("Workspace root dir:", data)
        )

    def on_dispose(self):
        print("Template Service Plugin disposed")


plugin = TemplateServicePlugin()

if __name__ == "__main__":
    plugin.start()
