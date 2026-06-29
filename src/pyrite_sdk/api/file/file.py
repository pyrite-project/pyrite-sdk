from __future__ import annotations
from typing import Callable, Optional, TYPE_CHECKING
from ...models.schema import (
    request,
    FileRequestPathPayload,
    FileRequestCreatePayload,
    FileRequestRenamePayload,
    FileRequestCopyPayload,
    FileRequestWritePayload,
    FileRequestUploadPayload,
    FileRequestUniqueNamePayload,
)
if TYPE_CHECKING:
    from ...core.bridge import Bridge


class File:
    def __init__(self, bridge: Bridge):
        self._bridge = bridge

    def get_file_list(self, path: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.file.get_dir_list",
                data=path,
            ),
            callback=callback,
        )

    def get_root_dir(self, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request("sdk.file.get_root_dir"),
            callback=callback,
        )

    def save_current_file(self):
        self._bridge.push(
            request("sdk.file.save_current_file"),
        )

    def save_current_file_as(self):
        self._bridge.push(
            request("sdk.file.save_current_file_as"),
        )

    def create_file(
        self,
        path: str,
        callback: Optional[Callable] = None,
    ):
        self._bridge.push_wait_response(
            request(
                "sdk.file.create_file",
                payload=FileRequestCreatePayload(path=path),
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
                "sdk.file.create_folder",
                payload=FileRequestCreatePayload(path=path),
            ),
            callback=callback,
        )

    def get_focus_file_node(self, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request("sdk.file.get_focus_file_node"),
            callback=callback,
        )

    def get_focus_folder_node(self, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request("sdk.file.get_focus_folder_node"),
            callback=callback,
        )

    def open_file(self, path: str):
        self._bridge.push(
            request(
                "sdk.file.open_file",
                payload=FileRequestPathPayload(path=path),
            ),
        )

    def upload_selected_local_file_item(self):
        self._bridge.push(
            request("sdk.file.upload_selected_local_file_item"),
        )

    def rename(self, path: str, new_name: str):
        self._bridge.push(
            request(
                "sdk.file.rename",
                payload=FileRequestRenamePayload(
                    path=path,
                    new_name=new_name,
                ),
            ),
        )

    def delete(self, path: str):
        self._bridge.push(
            request(
                "sdk.file.delete",
                payload=FileRequestPathPayload(path=path),
            ),
        )

    def open_folder(self, path: str):
        self._bridge.push(
            request(
                "sdk.file.open_folder",
                payload=FileRequestPathPayload(path=path),
            ),
        )

    def is_file(self, path: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.file.is_file",
                payload=FileRequestPathPayload(path=path),
            ),
            callback=callback,
        )

    def is_directory(self, path: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.file.is_directory",
                payload=FileRequestPathPayload(path=path),
            ),
            callback=callback,
        )

    def read_file(self, path: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.file.read_file",
                payload=FileRequestPathPayload(path=path),
            ),
            callback=callback,
        )

    def write_file(self, path: str, content: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.file.write_file",
                payload=FileRequestWritePayload(path=path, content=content),
            ),
            callback=callback,
        )

    def copy_file(self, src: str, dst: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.file.copy_file",
                payload=FileRequestCopyPayload(src=src, dst=dst),
            ),
            callback=callback,
        )

    def move_file(self, src: str, dst: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.file.move_file",
                payload=FileRequestCopyPayload(src=src, dst=dst),
            ),
            callback=callback,
        )

    def exists(self, path: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.file.exists",
                payload=FileRequestPathPayload(path=path),
            ),
            callback=callback,
        )

    def upload_file(self, local_path: str, board_path: str, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.file.upload_file",
                payload=FileRequestUploadPayload(
                    local_path=local_path,
                    board_path=board_path,
                ),
            ),
            callback=callback,
        )

    def get_unique_name(self, name: str, is_folder: bool = False, callback: Optional[Callable] = None):
        self._bridge.push_wait_response(
            request(
                "sdk.file.get_unique_name",
                payload=FileRequestUniqueNamePayload(
                    name=name,
                    is_folder=is_folder,
                ),
            ),
            callback=callback,
        )
