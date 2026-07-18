from pyrite_sdk.api.ui.widgets import *
from pyrite_sdk.api.ui.page import Page
from pyrite_sdk.api.ui.event import Event
from pyrite_sdk.api.ui.sentence import *
from pyrite_sdk.models.consts import Package, Ui
from pyrite_sdk.core.plugin import UiPlugin

page = Page(packages=[Package.core.widgets, Package.core.material])

root = NewWidget(Ui.root).add_to(page)

with Scaffold(
    app_bar=AppBar(title=Text("Plugin Test")),
).add_to(root):
    with Container():
        with SingleChildScrollView():
            with Column():

                # ── Local Workspace Tests ──

                Text("=== File ===", style={"fontSize": 18.0})

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.file.get_root_dir(
                        lambda **cb: plugin.bridge.let(data.r0, str(cb))
                    ), args={"id": 0})):
                    Text("Get Root Dir")

                Text(data.r0)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.file.get_file_list(
                        "/",
                        lambda **cb: plugin.bridge.let(data.r1, str(cb))
                    ), args={"id": 1})):
                    Text("Get File List (/)")

                Text(data.r1)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.file.get_focus_file_node(
                        lambda **cb: plugin.bridge.let(data.r2, str(cb))
                    ), args={"id": 2})):
                    Text("Get Focus File Node")

                Text(data.r2)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.file.get_focus_folder_node(
                        lambda **cb: plugin.bridge.let(data.r3, str(cb))
                    ), args={"id": 3})):
                    Text("Get Focus Folder Node")

                Text(data.r3)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.file.create_file(
                        path="/test_plugin.txt",
                        callback=lambda **cb: plugin.bridge.let(data.r4, str(cb))
                    ), args={"id": 4})):
                    Text("Create File (/test_plugin.txt)")

                Text(data.r4)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.file.create_folder(
                        path="/test_plugin_dir",
                        callback=lambda **cb: plugin.bridge.let(data.r5, str(cb))
                    ), args={"id": 5})):
                    Text("Create Folder (/test_plugin_dir)")

                Text(data.r5)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.file.rename(
                        path="/data.r6_target.txt",
                        new_name="data.r6_renamed.txt",
                    ), args={"id": 6})):
                    Text("Rename (test)")

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.file.delete(
                        path="/test_plugin.txt",
                    ), args={"id": 7})):
                    Text("Delete (test_plugin.txt)")

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.file.is_file(
                        path="/test_plugin.txt",
                        callback=lambda **cb: plugin.bridge.let(data.r6, str(cb))
                    ), args={"id": 8})):
                    Text("Is File (/test_plugin.txt)")

                Text(data.r6)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.file.is_directory(
                        path="/test_plugin_dir",
                        callback=lambda **cb: plugin.bridge.let(data.r7, str(cb))
                    ), args={"id": 9})):
                    Text("Is Dir (/test_plugin_dir)")

                Text(data.r7)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.file.open_folder(
                        path="/",
                    ), args={"id": 10})):
                    Text("Open Folder (/)")

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.file.get_unique_name(
                        name="/new_file.txt",
                        is_folder=False,
                        callback=lambda **cb: plugin.bridge.let(data.r25, str(cb))
                    ), args={"id": 37})):
                    Text("Get Unique Name (file)")

                Text(data.r25)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.file.get_unique_name(
                        name="/new_folder",
                        is_folder=True,
                        callback=lambda **cb: plugin.bridge.let(data.r26, str(cb))
                    ), args={"id": 38})):
                    Text("Get Unique Name (folder)")

                Text(data.r26)

                # ── Board Workspace Tests ──

                Text("=== Board ===", style={"fontSize": 18.0})

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.board.get_root_dir(
                        lambda **cb: plugin.bridge.let(data.r8, str(cb))
                    ), args={"id": 11})):
                    Text("Board: Get Root Dir")

                Text(data.r8)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.board.get_dir_list(
                        "/",
                        lambda **cb: plugin.bridge.let(data.r9, str(cb))
                    ), args={"id": 12})):
                    Text("Board: Get Dir List (/)")

                Text(data.r9)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.board.get_focus_file_node(
                        lambda **cb: plugin.bridge.let(data.r10, str(cb))
                    ), args={"id": 13})):
                    Text("Board: Get Focus File Node")

                Text(data.r10)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.board.get_focus_folder_node(
                        lambda **cb: plugin.bridge.let(data.r11, str(cb))
                    ), args={"id": 14})):
                    Text("Board: Get Focus Folder Node")

                Text(data.r11)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.board.get_corresponding_file_path(
                        path="/board_file.txt",
                        callback=lambda **cb: plugin.bridge.let(data.r12, str(cb))
                    ), args={"id": 15})):
                    Text("Board: Get Corresponding File Path")

                Text(data.r12)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.board.is_file(
                        path="/board_file.txt",
                        callback=lambda **cb: plugin.bridge.let(data.r13, str(cb))
                    ), args={"id": 16})):
                    Text("Board: Is File")

                Text(data.r13)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.board.is_directory(
                        path="/board_dir",
                        callback=lambda **cb: plugin.bridge.let(data.r14, str(cb))
                    ), args={"id": 17})):
                    Text("Board: Is Directory")

                Text(data.r14)

                # ── Local: remaining commands ──

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.file.save_current_file(),
                    args={"id": 18})):
                    Text("Local: Save Current File")

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.file.save_current_file_as(),
                    args={"id": 19})):
                    Text("Local: Save Current File As")

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.file.open_file("/"),
                    args={"id": 20})):
                    Text("Local: Open File (/)")

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.file.upload_selected_local_file_item(),
                    args={"id": 21})):
                    Text("Local: Upload Selected File Item")

                # ── Board: remaining commands ──

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.board.open_file("/"),
                    args={"id": 22})):
                    Text("Board: Open File (/)")

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.board.download_selected_board_item(),
                    args={"id": 23})):
                    Text("Board: Download Selected Board Item")

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.board.rename(
                        path="/board_file.txt",
                        new_name="board_file_renamed.txt",
                    ), args={"id": 24})):
                    Text("Board: Rename")

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.board.delete_file("/board_file.txt"),
                    args={"id": 25})):
                    Text("Board: Delete File")

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.board.delete_folder("/board_dir"),
                    args={"id": 26})):
                    Text("Board: Delete Folder")

                # ── Local: New file ops ──

                Text("=== Local File Ops ===", style={"fontSize": 18.0})

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.file.read_file(
                        path="/test_plugin.txt",
                        callback=lambda **cb: plugin.bridge.let(data.r15, str(cb))
                    ), args={"id": 27})):
                    Text("Local: Read File")

                Text(data.r15)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.file.write_file(
                        path="/test_plugin.txt",
                        content="Hello from plugin!",
                        callback=lambda **cb: plugin.bridge.let(data.r16, str(cb))
                    ), args={"id": 28})):
                    Text("Local: Write File")

                Text(data.r16)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.file.copy_file(
                        src="/test_plugin.txt",
                        dst="/test_plugin_copy.txt",
                        callback=lambda **cb: plugin.bridge.let(data.r17, str(cb))
                    ), args={"id": 29})):
                    Text("Local: Copy File")

                Text(data.r17)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.file.move_file(
                        src="/test_plugin_copy.txt",
                        dst="/test_plugin_moved.txt",
                        callback=lambda **cb: plugin.bridge.let(data.r18, str(cb))
                    ), args={"id": 30})):
                    Text("Local: Move File")

                Text(data.r18)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.file.exists(
                        path="/test_plugin.txt",
                        callback=lambda **cb: plugin.bridge.let(data.r19, str(cb))
                    ), args={"id": 31})):
                    Text("Local: Exists (/test_plugin.txt)")

                Text(data.r19)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.file.upload_file(
                        local_path="/test_plugin.txt",
                        board_path="/uploaded_from_plugin.txt",
                        callback=lambda **cb: plugin.bridge.let(data.r20, str(cb))
                    ), args={"id": 32})):
                    Text("Local: Upload File to Board")

                Text(data.r20)

                # ── Board: New file ops ──

                Text("=== Board File Ops ===", style={"fontSize": 18.0})

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.board.read_file(
                        path="/board_file.txt",
                        callback=lambda **cb: plugin.bridge.let(data.r21, str(cb))
                    ), args={"id": 33})):
                    Text("Board: Read File")

                Text(data.r21)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.board.write_file(
                        path="/board_from_plugin.txt",
                        content="Written by plugin!",
                        callback=lambda **cb: plugin.bridge.let(data.r22, str(cb))
                    ), args={"id": 34})):
                    Text("Board: Write File")

                Text(data.r22)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.board.exists(
                        path="/board_file.txt",
                        callback=lambda **cb: plugin.bridge.let(data.r23, str(cb))
                    ), args={"id": 35})):
                    Text("Board: Exists (/board_file.txt)")

                Text(data.r23)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.board.download_file(
                        board_path="/board_file.txt",
                        local_path="/downloaded_from_board.txt",
                        callback=lambda **cb: plugin.bridge.let(data.r24, str(cb))
                    ), args={"id": 36})):
                    Text("Board: Download File to Local")

                Text(data.r24)

                # ── Editor Tests ──

                Text("=== Editor ===", style={"fontSize": 18.0})

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.editor.get_text(
                        callback=lambda **cb: plugin.bridge.let(data.r27, str(cb))
                    ), args={"id": 39})):
                    Text("Editor: Get Text")

                Text(data.r27)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.editor.set_text("Hello from plugin!"),
                    args={"id": 40})):
                    Text("Editor: Set Text")

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.editor.get_line_count(
                        callback=lambda **cb: plugin.bridge.let(data.r28, str(cb))
                    ), args={"id": 41})):
                    Text("Editor: Get Line Count")

                Text(data.r28)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.editor.get_cursor_position(
                        callback=lambda **cb: plugin.bridge.let(data.r29, str(cb))
                    ), args={"id": 42})):
                    Text("Editor: Get Cursor Position")

                Text(data.r29)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.editor.set_cursor_position(line=0, column=0),
                    args={"id": 43})):
                    Text("Editor: Set Cursor (0,0)")

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.editor.select_all(),
                    args={"id": 44})):
                    Text("Editor: Select All")

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.editor.get_selected_text(
                        callback=lambda **cb: plugin.bridge.let(data.r30, str(cb))
                    ), args={"id": 45})):
                    Text("Editor: Get Selected Text")

                Text(data.r30)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.editor.copy(),
                    args={"id": 46})):
                    Text("Editor: Copy")

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.editor.paste(),
                    args={"id": 47})):
                    Text("Editor: Paste")

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.editor.undo(),
                    args={"id": 48})):
                    Text("Editor: Undo")

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.editor.redo(),
                    args={"id": 49})):
                    Text("Editor: Redo")

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.editor.find(
                        word="plugin",
                        callback=lambda **cb: plugin.bridge.let(data.r31, str(cb))
                    ), args={"id": 50})):
                    Text("Editor: Find 'plugin'")

                Text(data.r31)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.editor.clear_search(),
                    args={"id": 51})):
                    Text("Editor: Clear Search")

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.editor.go_to_line(line=0),
                    args={"id": 52})):
                    Text("Editor: Go to Line 0")

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.editor.get_current_tab(
                        callback=lambda **cb: plugin.bridge.let(data.r32, str(cb))
                    ), args={"id": 53})):
                    Text("Editor: Get Current Tab")

                Text(data.r32)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.editor.list_tabs(
                        callback=lambda **cb: plugin.bridge.let(data.r33, str(cb))
                    ), args={"id": 54})):
                    Text("Editor: List Tabs")

                Text(data.r33)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.editor.set_ghost_text(
                        text="# AI suggestion",
                        line=0,
                        column=0,
                    ), args={"id": 55})):
                    Text("Editor: Set Ghost Text")

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.editor.clear_ghost_text(),
                    args={"id": 56})):
                    Text("Editor: Clear Ghost Text")

                # ── Router Tests ──

                Text("=== Router ===", style={"fontSize": 18.0})

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.router.push("settings"),
                    args={"id": 60})):
                    Text("Router: Push Settings")

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.router.push("about"),
                    args={"id": 61})):
                    Text("Router: Push About")

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.router.pop(),
                    args={"id": 62})):
                    Text("Router: Pop")

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.router.replace("settings"),
                    args={"id": 63})):
                    Text("Router: Replace with Settings")

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.router.goto("about"),
                    args={"id": 64})):
                    Text("Router: Goto About")

                # ── Persistence Tests ──

                Text("=== Persistence ===", style={"fontSize": 18.0})

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.persistence.set(
                        "test_group", "hello", "world",
                        callback=lambda **cb: plugin.bridge.let(data.r40, str(cb))
                    ), args={"id": 70})):
                    Text("Persist: Set (test_group.hello = world)")

                Text(data.r40)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.persistence.get(
                        "test_group", "hello",
                        callback=lambda **cb: plugin.bridge.let(data.r41, str(cb))
                    ), args={"id": 71})):
                    Text("Persist: Get (test_group.hello)")

                Text(data.r41)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.persistence.set(
                        "test_group", "count", 42,
                        callback=lambda **cb: plugin.bridge.let(data.r42, str(cb))
                    ), args={"id": 72})):
                    Text("Persist: Set (test_group.count = 42)")

                Text(data.r42)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.persistence.get(
                        "test_group", "count",
                        callback=lambda **cb: plugin.bridge.let(data.r43, str(cb))
                    ), args={"id": 73})):
                    Text("Persist: Get (test_group.count)")

                Text(data.r43)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.persistence.set(
                        "another_group", "config", {"theme": "dark", "lang": "zh"},
                        callback=lambda **cb: plugin.bridge.let(data.r44, str(cb))
                    ), args={"id": 74})):
                    Text("Persist: Set (another_group.config = dict)")

                Text(data.r44)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.persistence.get(
                        "another_group", "config",
                        callback=lambda **cb: plugin.bridge.let(data.r45, str(cb))
                    ), args={"id": 75})):
                    Text("Persist: Get (another_group.config)")

                Text(data.r45)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.persistence.list_groups(
                        callback=lambda **cb: plugin.bridge.let(data.r46, str(cb))
                    ), args={"id": 76})):
                    Text("Persist: List Groups")

                Text(data.r46)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.persistence.list_keys(
                        "test_group",
                        callback=lambda **cb: plugin.bridge.let(data.r47, str(cb))
                    ), args={"id": 77})):
                    Text("Persist: List Keys (test_group)")

                Text(data.r47)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.persistence.delete(
                        "test_group", "hello",
                        callback=lambda **cb: plugin.bridge.let(data.r48, str(cb))
                    ), args={"id": 78})):
                    Text("Persist: Delete (test_group.hello)")

                Text(data.r48)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.persistence.get(
                        "test_group", "hello",
                        callback=lambda **cb: plugin.bridge.let(data.r49, str(cb))
                    ), args={"id": 79})):
                    Text("Persist: Get after Delete (should be null)")

                Text(data.r49)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.persistence.clear(
                        "test_group",
                        callback=lambda **cb: plugin.bridge.let(data.r50, str(cb))
                    ), args={"id": 80})):
                    Text("Persist: Clear (test_group)")

                Text(data.r50)

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.persistence.list_keys(
                        "test_group",
                        callback=lambda **cb: plugin.bridge.let(data.r51, str(cb))
                    ), args={"id": 81})):
                    Text("Persist: List Keys after Clear (should be [])")

                Text(data.r51)

# ── Settings Page ──

settings_page = Page(packages=[Package.core.widgets, Package.core.material])

settings_root = NewWidget(Ui.root).add_to(settings_page)

with Scaffold(
    app_bar=AppBar(title=Text("Settings")),
).add_to(settings_root):
    with Container():
        with SingleChildScrollView():
            with Column():

                Text("=== Settings Page ===", style={"fontSize": 18.0})
                Text("This is the settings page.")
                Text("You navigated here from the home page.")

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.router.pop(),
                    args={"id": 100})):
                    Text("Go Back (pop)")

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.router.goto("home"),
                    args={"id": 101})):
                    Text("Go to Home (goto)")

# ── About Page ──

about_page = Page(packages=[Package.core.widgets, Package.core.material])

about_root = NewWidget(Ui.root).add_to(about_page)

with Scaffold(
    app_bar=AppBar(title=Text("About")),
).add_to(about_root):
    with Container():
        with SingleChildScrollView():
            with Column():

                Text("=== About Page ===", style={"fontSize": 18.0})
                Text("This is the about page.")
                Text("Multi-page routing demo.")

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.router.pop(),
                    args={"id": 200})):
                    Text("Go Back (pop)")

                with ElevatedButton(on_pressed=Event(
                    lambda **kws: plugin.router.replace("home"),
                    args={"id": 201})):
                    Text("Replace with Home")

# Add navigation buttons to home page (append before page.print_tree)

home_nav_root = root  # root is already the home page's root widget

class MyPlugin(UiPlugin):
    def __init__(self):
        super().__init__()
        self.pages = {
            "home": page,
            "settings": settings_page,
            "about": about_page,
        }

    def on_start(self):
        print("Plugin started")

    def on_dispose(self):
        print("Plugin disposed")


plugin = MyPlugin()

if __name__ == "__main__":
    plugin.start()
