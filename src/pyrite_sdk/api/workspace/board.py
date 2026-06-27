from __future__ import annotations
from typing import Callable, Optional, TYPE_CHECKING
from ...models.schema import (
    request,
    LocalWorkspaceRequestPathPayload,
    LocalWorkspaceRequestRenamePayload,
    LocalWorkspaceRequestWritePayload,
    LocalWorkspaceRequestDownloadPayload,
)
if TYPE_CHECKING:
    from ...core.bridge import Bridge


class BoardWorkspace:
    def __init__(self, bridge: Optional[Bridge] = None):
        self._bridge = bridge

    def get_dir_list(self, path: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.board_workspace.get_dir_list",
                data=path,
            ),
            callback=callback,
        )

    def get_root_dir(self, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request("sdk.board_workspace.get_root_dir"),
            callback=callback,
        )

    def get_focus_file_node(self, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request("sdk.board_workspace.get_focus_file_node"),
            callback=callback,
        )

    def get_focus_folder_node(self, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request("sdk.board_workspace.get_focus_folder_node"),
            callback=callback,
        )

    def open_file(self, path: str):
        self._bridge.push(
            request(
                "sdk.board_workspace.open_file",
                payload=LocalWorkspaceRequestPathPayload(path=path),
            ),
        )

    def download_selected_board_item(self):
        self._bridge.push(
            request("sdk.board_workspace.download_selected_board_item"),
        )

    def rename(self, path: str, new_name: str):
        self._bridge.push(
            request(
                "sdk.board_workspace.rename",
                payload=LocalWorkspaceRequestRenamePayload(
                    path=path,
                    new_name=new_name,
                ),
            ),
        )

    def delete_file(self, path: str):
        self._bridge.push(
            request(
                "sdk.board_workspace.delete_file",
                payload=LocalWorkspaceRequestPathPayload(path=path),
            ),
        )

    def delete_folder(self, path: str):
        self._bridge.push(
            request(
                "sdk.board_workspace.delete_folder",
                payload=LocalWorkspaceRequestPathPayload(path=path),
            ),
        )

    def is_file(self, path: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.board_workspace.is_file",
                payload=LocalWorkspaceRequestPathPayload(path=path),
            ),
            callback=callback,
        )

    def is_directory(self, path: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.board_workspace.is_directory",
                payload=LocalWorkspaceRequestPathPayload(path=path),
            ),
            callback=callback,
        )

    def get_corresponding_file_path(self, path: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.board_workspace.get_corresponding_file_path",
                payload=LocalWorkspaceRequestPathPayload(path=path),
            ),
            callback=callback,
        )

    def read_file(self, path: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.board_workspace.read_file",
                payload=LocalWorkspaceRequestPathPayload(path=path),
            ),
            callback=callback,
        )

    def write_file(self, path: str, content: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.board_workspace.write_file",
                payload=LocalWorkspaceRequestWritePayload(path=path, content=content),
            ),
            callback=callback,
        )

    def exists(self, path: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.board_workspace.exists",
                payload=LocalWorkspaceRequestPathPayload(path=path),
            ),
            callback=callback,
        )

    def download_file(self, board_path: str, local_path: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.board_workspace.download_file",
                payload=LocalWorkspaceRequestDownloadPayload(
                    board_path=board_path,
                    local_path=local_path,
                ),
            ),
            callback=callback,
        )
