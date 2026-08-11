from __future__ import annotations

from typing import Any, Callable, Optional, TYPE_CHECKING

from ..models.schema import DialogOpenFilePayload, request

if TYPE_CHECKING:
    from ..core.bridge import Bridge


class Dialog:
    def __init__(self, bridge: Bridge) -> None:
        self._bridge = bridge

    def open_folder(
        self,
        title: Optional[str] = None,
        initial_directory: Optional[str] = None,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.dialog.open_folder",
                payload=DialogOpenFilePayload(
                    title=title,
                    initial_directory=initial_directory,
                ),
            ),
            callback=callback,
        )

    def open_file(
        self,
        title: Optional[str] = None,
        initial_directory: Optional[str] = None,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.dialog.open_file",
                payload=DialogOpenFilePayload(
                    title=title,
                    initial_directory=initial_directory,
                ),
            ),
            callback=callback,
        )

    def open_files(
        self,
        title: Optional[str] = None,
        initial_directory: Optional[str] = None,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.dialog.open_files",
                payload=DialogOpenFilePayload(
                    title=title,
                    initial_directory=initial_directory,
                ),
            ),
            callback=callback,
        )
