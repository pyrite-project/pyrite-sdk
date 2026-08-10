from __future__ import annotations

from typing import Any, Callable, Optional, TYPE_CHECKING

from ..models.schema import DialogOpenFolderPayload, request

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
                payload=DialogOpenFolderPayload(
                    title=title,
                    initial_directory=initial_directory,
                ),
            ),
            callback=callback,
        )
