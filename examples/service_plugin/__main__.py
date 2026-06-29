from pyrite_sdk.core.plugin import Plugin


class FileWatcherPlugin(Plugin):
    def __init__(self):
        super().__init__()
        self._watching = False

    def on_start(self):
        print("File Watcher: started")
        self._watching = True
        self._scan_files()

    def on_dispose(self):
        print("File Watcher: disposed")
        self._watching = False

    def on_pause(self):
        print("File Watcher: paused")

    def on_resume(self):
        print("File Watcher: resumed")
        self._scan_files()

    def _scan_files(self):
        """Scan workspace root directory."""
        self.local_workspace.get_root_dir(
            lambda **cb: self._on_root_dir(cb)
        )

    def _on_root_dir(self, result):
        root = result.get("path", "")
        if root:
            print(f"File Watcher: workspace root = {root}")
            self.local_workspace.get_dir_list(
                "/",
                lambda **cb: self._on_file_list(cb)
            )
        else:
            print("File Watcher: no workspace root found")

    def _on_file_list(self, result):
        files = result.get("dir_list", [])
        print(f"File Watcher: found {len(files)} items in workspace")
        for f in files[:10]:
            print(f"  - {f}")
        if len(files) > 10:
            print(f"  ... and {len(files) - 10} more")


plugin = FileWatcherPlugin()
plugin.start()
