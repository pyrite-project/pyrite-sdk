from typing import Callable, TYPE_CHECKING
from ...models.schema import request
if TYPE_CHECKING:
    from ...core.bridge import Bridge

class LocalWorkspace:
    def __init__(self, bridge: Bridge):
        self._bridge = bridge
        
    def get_file_list(self, path: str, callback: Callable):
        self._bridge.push_wait_response(
            request(
                "sdk.local_workspace.get_dir_list",
                data=path
            ),
            callback=callback
        )
    
    def get_root_dir(self, callback: Callable):
        pass
        
    def save_current_file(self):
        pass
    
    def save_current_file_as(self):
        pass

    def create_file(self):
        pass
    
    def create_folder(self):
        pass

    def get_focus_file_node(self):
        pass

    def get_focus_folder_node(self):
        pass

    def open_file():
        pass

    def upload_selected_local_file_item():
        pass

    def rename_file(self, path: str, new_name: str):
        pass

    def delete_file(self, path: str):
        pass

    def open_folder():
        pass