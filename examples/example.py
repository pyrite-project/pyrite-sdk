from pyrite_sdk.api.ui.widgets import *
from pyrite_sdk.api.ui.page import Page
from pyrite_sdk.api.ui.event import Event
from pyrite_sdk.api.ui.sentence import *
from pyrite_sdk.models.schema import request, OkResponsePayload
from pyrite_sdk.models.consts import Package, Ui
from pyrite_sdk.core.plugin import Plugin

def callback(**kws):
    """Callback handler for custom widget events."""
    print("callback-custom-widget", kws)
    plugin.bridge.push(request("sdk.request", OkResponsePayload(data="CallbackMessage")))
    plugin.bridge.let(data.x, "Pyrite")

    ws = plugin.local_workspace
    ws.get_root_dir(lambda **kws: print("callback-get-root-dir", kws))
    ws.get_file_list("/", lambda **kws: print("callback-get-file-list", kws))
    ws.get_focus_file_node(lambda **kws: print("callback-get-focus-file-node", kws))
    ws.get_focus_folder_node(lambda **kws: print("callback-get-focus-folder-node", kws))
    ws.create_file(name="test.txt", callback=lambda **kws: print("callback-create-file", kws))
    ws.create_folder(name="test_dir", callback=lambda **kws: print("callback-create-folder", kws))

page = Page(packages=[Package.core.widgets, Package.core.material])
button = NewWidget("Button", states={"down": False}).add_to(page)

with GestureDetector(
        on_tap_down=let(state.down, True),
        on_tap_up=let(state.down, False),
        on_tap_cancel=let(state.down, False),
        on_tap=args.on_pressed).add_to(button):
    with Container(
        margin=Match(
            state.down,
            Case(False, [0.0, 0.0, 8.0, 8.0]),
            Case(True, [8.0, 8.0, 0.0, 0.0])
        ),
        decoration={
            "type": "box",
            "border": [{}]
        }
    ):
        VarWidget(args.child)

root = NewWidget(Ui.root).add_to(page)
with Container().add_to(root):
    with Column():
        Text(["Hello, ", data.x], text_direction=Ui.LTR)
        with TextButton(on_pressed=Event(lambda **kws: print("callback", kws), args={"id": 0})):
            Text(["Hello, ", data.x], text_direction=Ui.LTR)
        with Widget("Button", on_pressed=Event(lambda **kws: callback(**kws), args={"id": 1})):
            with TextButton():
                Text(["Hello, ", data.x], text_direction=Ui.LTR)

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

if __name__ == "__main__":
    plugin = MyPlugin()
    plugin.start()
