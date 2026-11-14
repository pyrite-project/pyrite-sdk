from __future__ import annotations
from collections.abc import Mapping
from typing import Callable, Optional, Any, TYPE_CHECKING
from ...models.schema import request

if TYPE_CHECKING:
    from ...core.bridge import Bridge

_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")


def _is_theme_color(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return 0 <= value <= 0xFFFFFFFF
    if isinstance(value, str):
        digits = value[1:] if value.startswith("#") else value
        return len(digits) in (6, 8) and all(char in _HEX_DIGITS for char in digits)
    return False


def _validate_terminal_color(key: str, value: Any) -> None:
    if not _is_theme_color(value):
        raise ValueError(
            f"{key} must be an ARGB integer or a #RRGGBB/#AARRGGBB color, got {value!r}"
        )


def _validate_terminal_ansi(value: Any) -> list[Any]:
    if not isinstance(value, (list, tuple)):
        raise ValueError("terminal.ansi must be a list of exactly 16 colors")
    if len(value) != 16:
        raise ValueError(
            f"terminal.ansi must contain exactly 16 colors, got {len(value)}"
        )
    for index, color in enumerate(value):
        if not _is_theme_color(color):
            raise ValueError(
                "terminal.ansi must contain only ARGB integers or "
                f"#RRGGBB/#AARRGGBB colors; index {index} is {color!r}"
            )
    return list(value)


def _with_terminal_fields(
    data: Any,
    terminal_foreground: Any = None,
    terminal_background: Any = None,
    terminal_ansi: Any = None,
) -> Any:
    terminal_values = {
        "terminal.foreground": terminal_foreground,
        "terminal.background": terminal_background,
    }
    provided = {
        key: value for key, value in terminal_values.items() if value is not None
    }
    if terminal_ansi is not None:
        provided["terminal.ansi"] = terminal_ansi
    if not provided:
        return data
    if not isinstance(data, Mapping):
        raise TypeError(
            "theme data must be a mapping when terminal_* fields are provided"
        )
    for key, value in terminal_values.items():
        if value is not None:
            _validate_terminal_color(key, value)
    if terminal_ansi is not None:
        provided["terminal.ansi"] = _validate_terminal_ansi(terminal_ansi)
    merged = dict(data)
    merged.update(provided)
    return merged


class Theme:
    def __init__(self, bridge: Bridge) -> None:
        self._bridge = bridge

    def contribute(
        self,
        name: str,
        data: Any,
        callback: Optional[Callable[..., Any]] = None,
        *,
        terminal_foreground: Any = None,
        terminal_background: Any = None,
        terminal_ansi: Optional[list[Any]] = None,
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.theme.contribute",
                payload={
                    "name": name,
                    "data": _with_terminal_fields(
                        data,
                        terminal_foreground,
                        terminal_background,
                        terminal_ansi,
                    ),
                },
            ),
            callback=callback,
        )

    def register_runtime(
        self,
        name: str,
        data: Any,
        callback: Optional[Callable[..., Any]] = None,
        *,
        terminal_foreground: Any = None,
        terminal_background: Any = None,
        terminal_ansi: Optional[list[Any]] = None,
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.theme.register_runtime",
                payload={
                    "name": name,
                    "data": _with_terminal_fields(
                        data,
                        terminal_foreground,
                        terminal_background,
                        terminal_ansi,
                    ),
                },
            ),
            callback=callback,
        )

    def revoke(
        self,
        name: str,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._bridge.push_wait_response(
            request("sdk.theme.revoke", payload={"name": name}),
            callback=callback,
        )

    def get(
        self,
        name: str,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._bridge.push_wait_response(
            request(
                "sdk.theme.get",
                payload={"name": name},
            ),
            callback=callback,
        )

    def list(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._bridge.push_wait_response(
            request("sdk.theme.list"),
            callback=callback,
        )
