from __future__ import annotations

from typing import Any, Callable, Optional, TYPE_CHECKING

from ...models.schema import request

if TYPE_CHECKING:
    from ...core.bridge import Bridge

_CONFIGURATION_MODES = ("flat", "sectioned")
_SCOPES = ("auto", "runtime")


class Lsp:
    """Contribute language-server support as declarative profiles.

    A profile describes one language server without shipping code: matching
    rules recognize the launch, configuration keys map the IDE's common
    inputs (stubs paths, interpreter, strictness level) onto the server's own
    option shape, and environment templates carry values such as ``MYPYPATH``.

    Example::

        self.lsp.contribute(
            server_id="mylsp",
            match={"executables": ["mylsp"]},
            configuration={
                "mode": "sectioned",
                "section": "mylsp",
                "stubs_paths_key": "extraPaths",
                "python_executable_key": "pythonInterpreter",
                "type_checking_mode_key": "typeCheckingMode",
            },
            environment={"MYPYPATH": "{stubsPaths}"},
        )
    """

    def __init__(self, bridge: Bridge) -> None:
        self._bridge = bridge

    def contribute(
        self,
        server_id: str,
        configuration: dict[str, Any],
        match: Optional[dict[str, Any]] = None,
        label: str = "",
        environment: Optional[dict[str, str]] = None,
        scope: str = "auto",
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._validate_configuration(configuration)
        if scope not in _SCOPES:
            raise ValueError(f"scope 必须是 {' 或 '.join(_SCOPES)}: {scope}")
        if not match or not match.get("executables"):
            raise ValueError("match.executables 不能为空")
        self._bridge.push_wait_response(
            request(
                "sdk.lsp.contribute",
                payload={
                    "server_id": server_id,
                    "label": label,
                    "match": match,
                    "configuration": configuration,
                    "environment": environment or {},
                    "scope": scope,
                },
            ),
            callback=callback,
        )

    def register_runtime(
        self,
        server_id: str,
        configuration: dict[str, Any],
        match: Optional[dict[str, Any]] = None,
        label: str = "",
        environment: Optional[dict[str, str]] = None,
        scope: str = "runtime",
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._validate_configuration(configuration)
        if scope not in _SCOPES:
            raise ValueError(f"scope 必须是 {' 或 '.join(_SCOPES)}: {scope}")
        if not match or not match.get("executables"):
            raise ValueError("match.executables 不能为空")
        self._bridge.push_wait_response(
            request(
                "sdk.lsp.register_runtime",
                payload={
                    "server_id": server_id,
                    "label": label,
                    "match": match,
                    "configuration": configuration,
                    "environment": environment or {},
                    "scope": scope,
                },
            ),
            callback=callback,
        )

    def revoke(
        self,
        server_id: str,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._bridge.push_wait_response(
            request("sdk.lsp.revoke", payload={"server_id": server_id}),
            callback=callback,
        )

    def list(self, callback: Optional[Callable[..., Any]] = None) -> None:
        self._bridge.push_wait_response(request("sdk.lsp.list"), callback=callback)

    def get(
        self,
        server_id: str,
        callback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self._bridge.push_wait_response(
            request("sdk.lsp.get", payload={"server_id": server_id}),
            callback=callback,
        )

    @staticmethod
    def _validate_configuration(configuration: dict[str, Any]) -> None:
        if not isinstance(configuration, dict):
            raise ValueError("configuration 必须是对象")
        mode = configuration.get("mode", "flat")
        if mode not in _CONFIGURATION_MODES:
            raise ValueError(
                f"configuration.mode 必须是 {' 或 '.join(_CONFIGURATION_MODES)}: {mode}"
            )
        if mode == "sectioned" and not configuration.get("section"):
            raise ValueError("sectioned 配置缺少 section")
