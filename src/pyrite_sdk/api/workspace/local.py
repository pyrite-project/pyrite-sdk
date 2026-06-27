from __future__ import annotations
from typing import Callable, Optional, TYPE_CHECKING
from ...models.schema import (
    request,
    LocalWorkspaceRequestPathPayload,
    LocalWorkspaceRequestCreatePayload,
    LocalWorkspaceRequestRenamePayload,
    LocalWorkspaceRequestCopyPayload,
    LocalWorkspaceRequestWritePayload,
    LocalWorkspaceRequestUploadPayload,
    LocalWorkspaceRequestUniqueNamePayload,
)
if TYPE_CHECKING:
    from ...core.bridge import Bridge


class LocalWorkspace:
    def __init__(self, bridge: Bridge):
        self._bridge = bridge

    def get_file_list(self, path: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.local_workspace.get_dir_list",
                data=path,
            ),
            callback=callback,
        )

    def get_root_dir(self, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request("sdk.local_workspace.get_root_dir"),
            callback=callback,
        )

    def save_current_file(self):
        self._bridge.push(
            request("sdk.local_workspace.save_current_file"),
        )

    def save_current_file_as(self):
        self._bridge.push(
            request("sdk.local_workspace.save_current_file_as"),
        )

    def create_file(
        self,
        path: str,
        callback: Optional[Callable] = None,
    ):
        self._bridge.push_wait_response(
            request(
                "sdk.local_workspace.create_file",
                payload=LocalWorkspaceRequestCreatePayload(path=path),
            ),
            callback=callback,
        )

    def create_folder(
        self,
        path: str,
        callback: Optional[Callable] = None,
    ):
        self._bridge.push_wait_response(
            request(
                "sdk.local_workspace.create_folder",
                payload=LocalWorkspaceRequestCreatePayload(path=path),
            ),
            callback=callback,
        )

    def get_focus_file_node(self, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request("sdk.local_workspace.get_focus_file_node"),
            callback=callback,
        )

    def get_focus_folder_node(self, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request("sdk.local_workspace.get_focus_folder_node"),
            callback=callback,
        )

    def open_file(self, path: str):
        self._bridge.push(
            request(
                "sdk.local_workspace.open_file",
                payload=LocalWorkspaceRequestPathPayload(path=path),
            ),
        )

    def upload_selected_local_file_item(self):
        self._bridge.push(
            request("sdk.local_workspace.upload_selected_local_file_item"),
        )

    def rename(self, path: str, new_name: str):
        self._bridge.push(
            request(
                "sdk.local_workspace.rename",
                payload=LocalWorkspaceRequestRenamePayload(
                    path=path,
                    new_name=new_name,
                ),
            ),
        )

    def delete(self, path: str):
        self._bridge.push(
            request(
                "sdk.local_workspace.delete",
                payload=LocalWorkspaceRequestPathPayload(path=path),
            ),
        )

    def open_folder(self, path: str):
        self._bridge.push(
            request(
                "sdk.local_workspace.open_folder",
                payload=LocalWorkspaceRequestPathPayload(path=path),
            ),
        )

    def is_file(self, path: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.local_workspace.is_file",
                payload=LocalWorkspaceRequestPathPayload(path=path),
            ),
            callback=callback,
        )

    def is_directory(self, path: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.local_workspace.is_directory",
                payload=LocalWorkspaceRequestPathPayload(path=path),
            ),
            callback=callback,
        )

    def read_file(self, path: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.local_workspace.read_file",
                payload=LocalWorkspaceRequestPathPayload(path=path),
            ),
            callback=callback,
        )

    def write_file(self, path: str, content: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.local_workspace.write_file",
                payload=LocalWorkspaceRequestWritePayload(path=path, content=content),
            ),
            callback=callback,
        )

    def copy_file(self, src: str, dst: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.local_workspace.copy_file",
                payload=LocalWorkspaceRequestCopyPayload(src=src, dst=dst),
            ),
            callback=callback,
        )

    def move_file(self, src: str, dst: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.local_workspace.move_file",
                payload=LocalWorkspaceRequestCopyPayload(src=src, dst=dst),
            ),
            callback=callback,
        )

    def exists(self, path: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.local_workspace.exists",
                payload=LocalWorkspaceRequestPathPayload(path=path),
            ),
            callback=callback,
        )

    def upload_file(self, local_path: str, board_path: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.local_workspace.upload_file",
                payload=LocalWorkspaceRequestUploadPayload(
                    local_path=local_path,
                    board_path=board_path,
                ),
            ),
            callback=callback,
        )

    def get_unique_name(self, name: str, is_folder: bool = False, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.local_workspace.get_unique_name",
                payload=LocalWorkspaceRequestUniqueNamePayload(
                    name=name,
                    is_folder=is_folder,
                ),
            ),
            callback=callback,
        )
