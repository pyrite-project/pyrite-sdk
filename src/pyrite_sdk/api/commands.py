from __future__ import annotations

import inspect
import traceback
from typing import Any, Callable, Mapping, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.bridge import Bridge

CommandHandler = Callable[..., Any]


class Commands:
    """Register Manifest command handlers and dispatch ``ide.command.execute``."""

    def __init__(self, bridge: "Bridge") -> None:
        self._bridge = bridge
        self._handlers: dict[str, CommandHandler] = {}

    def register(self, command_id: str, handler: CommandHandler) -> None:
        if not command_id:
            raise ValueError("command_id is required")
        self._handlers[command_id] = handler

    def unregister(self, command_id: str) -> None:
        self._handlers.pop(command_id, None)

    def dispose_all(self) -> None:
        self._handlers.clear()

    async def dispatch(
        self,
        command_id: str,
        args: Optional[Mapping[str, Any]] = None,
        context: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        handler = self._handlers.get(command_id)
        if handler is None:
            raise LookupError(f"No handler registered for command: {command_id}")
        result = handler(
            args=dict(args or {}),
            context=dict(context or {}),
        )
        if inspect.isawaitable(result):
            return await result
        return result
