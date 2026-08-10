from __future__ import annotations
from typing import Any, Callable, Optional, TYPE_CHECKING
from ...models.schema import (
    request,
    FileRequestPathPayload,
    FileRequestRenamePayload,
    FileRequestWritePayload,
    FileRequestDownloadPayload,
)
if TYPE_CHECKING:
    from ...core.bridge import Bridge


class Board:
    def __init__(self, bridge: Optional[Bridge] = None) -> None:
        self._bridge: Optional[Bridge] = bridge

    def get_dir_list(
        self, path: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.board.get_dir_list",
                data=path,
            ),
            callback=callback,
        )

    def get_root_dir(
        self, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._bridge.push_wait_response(
            request("sdk.board.get_root_dir"),
            callback=callback,
        )

    def get_focus_file_node(
        self, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._bridge.push_wait_response(
            request("sdk.board.get_focus_file_node"),
            callback=callback,
        )

    def get_focus_folder_node(
        self, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._bridge.push_wait_response(
            request("sdk.board.get_focus_folder_node"),
            callback=callback,
        )

    def open_file(self, path: str) -> None:
        self._bridge.push(
            request(
                "sdk.board.open_file",
                payload=FileRequestPathPayload(path=path),
            ),
        )

    def download_selected_board_item(self) -> None:
        self._bridge.push(
            request("sdk.board.download_selected_board_item"),
        )

    def rename(self, path: str, new_name: str) -> None:
        self._bridge.push(
            request(
                "sdk.board.rename",
                payload=FileRequestRenamePayload(
                    path=path,
                    new_name=new_name,
                ),
            ),
        )

    def delete_file(self, path: str) -> None:
        self._bridge.push(
            request(
                "sdk.board.delete_file",
                payload=FileRequestPathPayload(path=path),
            ),
        )

    def delete_folder(self, path: str) -> None:
        self._bridge.push(
            request(
                "sdk.board.delete_folder",
                payload=FileRequestPathPayload(path=path),
            ),
        )

    def is_file(
        self, path: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.board.is_file",
                payload=FileRequestPathPayload(path=path),
            ),
            callback=callback,
        )

    def is_directory(
        self, path: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.board.is_directory",
                payload=FileRequestPathPayload(path=path),
            ),
            callback=callback,
        )

    def get_corresponding_file_path(
        self, path: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.board.get_corresponding_file_path",
                payload=FileRequestPathPayload(path=path),
            ),
            callback=callback,
        )

    def read_file(
        self, path: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.board.read_file",
                payload=FileRequestPathPayload(path=path),
            ),
            callback=callback,
        )

    def write_file(
        self,
        path: str,
        content: str,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.board.write_file",
                payload=FileRequestWritePayload(path=path, content=content),
            ),
            callback=callback,
        )

    def exists(
        self, path: str, callback: Optional[Callable[..., Any]] = None
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.board.exists",
                payload=FileRequestPathPayload(path=path),
            ),
            callback=callback,
        )

    def download_file(
        self,
        board_path: str,
        local_path: str,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.board.download_file",
                payload=FileRequestDownloadPayload(
                    board_path=board_path,
                    local_path=local_path,
                ),
            ),
            callback=callback,
        )
