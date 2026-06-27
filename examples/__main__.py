from pyrite_sdk.api.ui.widgets import *
from pyrite_sdk.api.ui.page import Page
from pyrite_sdk.api.ui.event import Event
from pyrite_sdk.api.ui.sentence import *
from pyrite_sdk.models.consts import Package, Ui
from pyrite_sdk.core.plugin import Plugin

page = Page(packages=[Package.core.widgets, Package.core.material])

root = NewWidget(Ui.root).add_to(page)

with Container().add_to(root):
    with Widget("SingleChildScrollView"):
        with Column():

            # ── Local Workspace Tests ──

            Text("=== Local Workspace ===", style={"fontSize": 18.0})

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.local_workspace.get_root_dir(
                    lambda **cb: plugin.bridge.let(data.r0, str(cb))
                ), args={"id": 0})):
                Text("Get Root Dir")

            Text(data.r0)

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.local_workspace.get_file_list(
                    "/",
                    lambda **cb: plugin.bridge.let(data.r1, str(cb))
                ), args={"id": 1})):
                Text("Get File List (/)")

            Text(data.r1)

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.local_workspace.get_focus_file_node(
                    lambda **cb: plugin.bridge.let(data.r2, str(cb))
                ), args={"id": 2})):
                Text("Get Focus File Node")

            Text(data.r2)

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.local_workspace.get_focus_folder_node(
                    lambda **cb: plugin.bridge.let(data.r3, str(cb))
                ), args={"id": 3})):
                Text("Get Focus Folder Node")

            Text(data.r3)

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.local_workspace.create_file(
                    path="/test_plugin.txt",
                    callback=lambda **cb: plugin.bridge.let(data.r4, str(cb))
                ), args={"id": 4})):
                Text("Create File (/test_plugin.txt)")

            Text(data.r4)

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.local_workspace.create_folder(
                    path="/test_plugin_dir",
                    callback=lambda **cb: plugin.bridge.let(data.r5, str(cb))
                ), args={"id": 5})):
                Text("Create Folder (/test_plugin_dir)")

            Text(data.r5)

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.local_workspace.rename(
                    path="/data.r6_target.txt",
                    new_name="data.r6_renamed.txt",
                ), args={"id": 6})):
                Text("Rename (test)")

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.local_workspace.delete(
                    path="/test_plugin.txt",
                ), args={"id": 7})):
                Text("Delete (test_plugin.txt)")

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.local_workspace.is_file(
                    path="/test_plugin.txt",
                    callback=lambda **cb: plugin.bridge.let(data.r6, str(cb))
                ), args={"id": 8})):
                Text("Is File (/test_plugin.txt)")

            Text(data.r6)

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.local_workspace.is_directory(
                    path="/test_plugin_dir",
                    callback=lambda **cb: plugin.bridge.let(data.r7, str(cb))
                ), args={"id": 9})):
                Text("Is Dir (/test_plugin_dir)")

            Text(data.r7)

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.local_workspace.open_folder(
                    path="/",
                ), args={"id": 10})):
                Text("Open Folder (/)")

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.local_workspace.get_unique_name(
                    name="/new_file.txt",
                    is_folder=False,
                    callback=lambda **cb: plugin.bridge.let(data.r25, str(cb))
                ), args={"id": 37})):
                Text("Get Unique Name (file)")

            Text(data.r25)

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.local_workspace.get_unique_name(
                    name="/new_folder",
                    is_folder=True,
                    callback=lambda **cb: plugin.bridge.let(data.r26, str(cb))
                ), args={"id": 38})):
                Text("Get Unique Name (folder)")

            Text(data.r26)

            # ── Board Workspace Tests ──

            Text("=== Board Workspace ===", style={"fontSize": 18.0})

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.board_workspace.get_root_dir(
                    lambda **cb: plugin.bridge.let(data.r8, str(cb))
                ), args={"id": 11})):
                Text("Board: Get Root Dir")

            Text(data.r8)

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.board_workspace.get_dir_list(
                    "/",
                    lambda **cb: plugin.bridge.let(data.r9, str(cb))
                ), args={"id": 12})):
                Text("Board: Get Dir List (/)")

            Text(data.r9)

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.board_workspace.get_focus_file_node(
                    lambda **cb: plugin.bridge.let(data.r10, str(cb))
                ), args={"id": 13})):
                Text("Board: Get Focus File Node")

            Text(data.r10)

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.board_workspace.get_focus_folder_node(
                    lambda **cb: plugin.bridge.let(data.r11, str(cb))
                ), args={"id": 14})):
                Text("Board: Get Focus Folder Node")

            Text(data.r11)

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.board_workspace.get_corresponding_file_path(
                    path="/board_file.txt",
                    callback=lambda **cb: plugin.bridge.let(data.r12, str(cb))
                ), args={"id": 15})):
                Text("Board: Get Corresponding File Path")

            Text(data.r12)

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.board_workspace.is_file(
                    path="/board_file.txt",
                    callback=lambda **cb: plugin.bridge.let(data.r13, str(cb))
                ), args={"id": 16})):
                Text("Board: Is File")

            Text(data.r13)

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.board_workspace.is_directory(
                    path="/board_dir",
                    callback=lambda **cb: plugin.bridge.let(data.r14, str(cb))
                ), args={"id": 17})):
                Text("Board: Is Directory")

            Text(data.r14)

            # ── Local: remaining commands ──

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.local_workspace.save_current_file(),
                args={"id": 18})):
                Text("Local: Save Current File")

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.local_workspace.save_current_file_as(),
                args={"id": 19})):
                Text("Local: Save Current File As")

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.local_workspace.open_file("/"),
                args={"id": 20})):
                Text("Local: Open File (/)")

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.local_workspace.upload_selected_local_file_item(),
                args={"id": 21})):
                Text("Local: Upload Selected File Item")

            # ── Board: remaining commands ──

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.board_workspace.open_file("/"),
                args={"id": 22})):
                Text("Board: Open File (/)")

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.board_workspace.download_selected_board_item(),
                args={"id": 23})):
                Text("Board: Download Selected Board Item")

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.board_workspace.rename(
                    path="/board_file.txt",
                    new_name="board_file_renamed.txt",
                ), args={"id": 24})):
                Text("Board: Rename")

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.board_workspace.delete_file("/board_file.txt"),
                args={"id": 25})):
                Text("Board: Delete File")

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.board_workspace.delete_folder("/board_dir"),
                args={"id": 26})):
                Text("Board: Delete Folder")

            # ── Local: New file ops ──

            Text("=== Local File Ops ===", style={"fontSize": 18.0})

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.local_workspace.read_file(
                    path="/test_plugin.txt",
                    callback=lambda **cb: plugin.bridge.let(data.r15, str(cb))
                ), args={"id": 27})):
                Text("Local: Read File")

            Text(data.r15)

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.local_workspace.write_file(
                    path="/test_plugin.txt",
                    content="Hello from plugin!",
                    callback=lambda **cb: plugin.bridge.let(data.r16, str(cb))
                ), args={"id": 28})):
                Text("Local: Write File")

            Text(data.r16)

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.local_workspace.copy_file(
                    src="/test_plugin.txt",
                    dst="/test_plugin_copy.txt",
                    callback=lambda **cb: plugin.bridge.let(data.r17, str(cb))
                ), args={"id": 29})):
                Text("Local: Copy File")

            Text(data.r17)

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.local_workspace.move_file(
                    src="/test_plugin_copy.txt",
                    dst="/test_plugin_moved.txt",
                    callback=lambda **cb: plugin.bridge.let(data.r18, str(cb))
                ), args={"id": 30})):
                Text("Local: Move File")

            Text(data.r18)

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.local_workspace.exists(
                    path="/test_plugin.txt",
                    callback=lambda **cb: plugin.bridge.let(data.r19, str(cb))
                ), args={"id": 31})):
                Text("Local: Exists (/test_plugin.txt)")

            Text(data.r19)

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.local_workspace.upload_file(
                    local_path="/test_plugin.txt",
                    board_path="/uploaded_from_plugin.txt",
                    callback=lambda **cb: plugin.bridge.let(data.r20, str(cb))
                ), args={"id": 32})):
                Text("Local: Upload File to Board")

            Text(data.r20)

            # ── Board: New file ops ──

            Text("=== Board File Ops ===", style={"fontSize": 18.0})

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.board_workspace.read_file(
                    path="/board_file.txt",
                    callback=lambda **cb: plugin.bridge.let(data.r21, str(cb))
                ), args={"id": 33})):
                Text("Board: Read File")

            Text(data.r21)

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.board_workspace.write_file(
                    path="/board_from_plugin.txt",
                    content="Written by plugin!",
                    callback=lambda **cb: plugin.bridge.let(data.r22, str(cb))
                ), args={"id": 34})):
                Text("Board: Write File")

            Text(data.r22)

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.board_workspace.exists(
                    path="/board_file.txt",
                    callback=lambda **cb: plugin.bridge.let(data.r23, str(cb))
                ), args={"id": 35})):
                Text("Board: Exists (/board_file.txt)")

            Text(data.r23)

            with Widget("ElevatedButton", onPressed=Event(
                lambda **kws: plugin.board_workspace.download_file(
                    board_path="/board_file.txt",
                    local_path="/downloaded_from_board.txt",
                    callback=lambda **cb: plugin.bridge.let(data.r24, str(cb))
                ), args={"id": 36})):
                Text("Board: Download File to Local")

            Text(data.r24)

page.print_tree(print_args=False)
print(page.to_rfw())


class MyPlugin(Plugin):
    def __init__(self):
        super().__init__()
        self.pages = {
            "home": page
        }

    def on_start(self):
        print("Plugin started")

    def on_dispose(self):
        print("Plugin disposed")


plugin = MyPlugin()
plugin.start()
