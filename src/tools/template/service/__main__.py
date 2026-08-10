from pyrite_sdk.core.plugin import ServicePlugin


class <PluginId>Plugin(ServicePlugin):
    def __init__(self):
        super().__init__()

    def on_start(self):
        print("<PluginId> Plugin started")
        self.file.get_root_dir(lambda data: print("Workspace root dir:", data))

    def on_dispose(self):
        print("<PluginId> Plugin disposed")


plugin = <PluginId>Plugin()

if __name__ == "__main__":
    plugin.start()
