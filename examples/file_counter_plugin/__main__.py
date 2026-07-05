from pyrite_sdk.api.ui import *
from pyrite_sdk.core.plugin import UiPlugin
from pyrite_sdk.models.consts import Package, Ui


def build_home_page(count: int):
    home_page = Page(packages=[Package.core.widgets, Package.core.material])
    home_root = NewWidget(Ui.root).add_to(home_page)
    with Scaffold(
        app_bar=AppBar(title=Text("File Counter Plugin")),
    ).add_to(home_root):
        with Column(
            cross_axis_alignment=CrossAxisAlignment.start,
            main_axis_alignment=MainAxisAlignment.center,
            main_axis_size=MainAxisSize.max,
        ):
            Text(
                ["Files Count:", str(count)],
                style=TextStyle(
                    font_size=20,
                    font_weight=FontWeight.bold,
                ),
            )
            with TextButton(Event(lambda **_: plugin.bridge.refresh())):
                Text("Refresh")
    return home_page


class FileCounterPlugin(UiPlugin):
    def __init__(self):
        super().__init__()
        self.count = 0
        self.pages = {
            "home": build_home_page(self.count),
        }

    def _render(self):
        self.pages["home"] = build_home_page(self.count)

    def on_refresh(self):
        print("File counter plugin refreshed")

        def root_dir_callback(**root):
            root_dir = root.get("data")
            if not root_dir:
                print("Failed to get root directory")
                return

            def file_list_callback(**files):
                self.count = len(files.get("data") or [])
                self._render()
                self.bridge.refresh(call_on_refresh=False)
                print(f"Found {self.count} files in {root_dir}")

            self.file.get_file_list(root_dir, file_list_callback)

        self.file.get_root_dir(root_dir_callback)

    def on_start(self):
        # self.on_refresh()
        print("File counter plugin started")

    def on_dispose(self):
        print("File counter plugin disposed")

plugin = FileCounterPlugin()
plugin.start()
