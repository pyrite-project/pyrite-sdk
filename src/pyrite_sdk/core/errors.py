from __future__ import annotations

from typing import Any, Mapping


class SdkApiError(Exception):
    """An error response returned by the IDE for an SDK API request."""

    def __init__(
        self,
        code: str,
        message: str,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


class PermissionDeniedError(SdkApiError):
    """The plugin does not have the permission required by an operation."""

    @property
    def required_permission(self) -> str | None:
        if isinstance(self.details, Mapping):
            required = self.details.get("required")
            return str(required) if required is not None else None
        return None


class UnknownCommandError(SdkApiError):
    """The connected IDE does not expose the requested SDK command."""


class InvalidPluginContextError(SdkApiError):
    """A response was rejected because its plugin session did not match."""


def api_error_from_payload(payload: Mapping[str, Any]) -> SdkApiError:
    code = str(payload.get("code", "internal_error"))
    message = str(payload.get("message", "SDK API request failed"))
    details = payload.get("details")
    error_type = {
        "permission_denied": PermissionDeniedError,
        "unknown_command": UnknownCommandError,
        "invalid_context": InvalidPluginContextError,
    }.get(code, SdkApiError)
    return error_type(code, message, details)
