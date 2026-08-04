from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path

PLUGIN_ID_ENV = "PYRITE_IDE_PLUGIN_ID"
PLUGIN_SESSION_ID_ENV = "PYRITE_IDE_PLUGIN_SESSION_ID"
PLUGIN_GENERATION_ENV = "PYRITE_IDE_PLUGIN_GENERATION"
PLUGIN_DIR_ENV = "PYRITE_IDE_PLUGIN_DIR"
PLUGIN_DATA_DIR_ENV = "PYRITE_IDE_PLUGIN_DATA_DIR"
PLUGIN_CACHE_DIR_ENV = "PYRITE_IDE_PLUGIN_CACHE_DIR"
PLUGIN_TEMP_DIR_ENV = "PYRITE_IDE_PLUGIN_TEMP_DIR"
PLUGIN_CAPABILITIES_ENV = "PYRITE_IDE_PLUGIN_CAPABILITIES"

PLUGIN_CONTEXT_ENV_VARS = (
    PLUGIN_ID_ENV,
    PLUGIN_SESSION_ID_ENV,
    PLUGIN_GENERATION_ENV,
    PLUGIN_DIR_ENV,
    PLUGIN_DATA_DIR_ENV,
    PLUGIN_CACHE_DIR_ENV,
    PLUGIN_TEMP_DIR_ENV,
    PLUGIN_CAPABILITIES_ENV,
)

__all__ = (
    "PLUGIN_ID_ENV",
    "PLUGIN_SESSION_ID_ENV",
    "PLUGIN_GENERATION_ENV",
    "PLUGIN_DIR_ENV",
    "PLUGIN_DATA_DIR_ENV",
    "PLUGIN_CACHE_DIR_ENV",
    "PLUGIN_TEMP_DIR_ENV",
    "PLUGIN_CAPABILITIES_ENV",
    "PLUGIN_CONTEXT_ENV_VARS",
    "PluginContext",
    "PluginContextError",
)


class PluginContextError(RuntimeError):
    """Raised when the host-provided plugin context is incomplete or invalid."""


def _required_value(environment: Mapping[str, str], name: str) -> str:
    value = environment.get(name)
    if value is None or not value.strip():
        raise PluginContextError(f"{name} must not be empty")
    return value


def _absolute_path(environment: Mapping[str, str], name: str) -> Path:
    value = _required_value(environment, name)
    path = Path(value)
    if not path.is_absolute():
        raise PluginContextError(f"{name} must be an absolute path: {value!r}")
    return path


def _capability_set(value: object, source: str) -> frozenset[str]:
    if not isinstance(value, (list, tuple, set, frozenset)):
        raise PluginContextError(f"{source} must be an array of strings")
    if any(
        not isinstance(item, str) or not item.strip()
        for item in value
    ):
        raise PluginContextError(
            f"{source} must contain only non-empty strings"
        )
    return frozenset(value)


def _payload_string(payload: Mapping[str, object], name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value:
        raise PluginContextError(
            f"pluginContext.{name} must be a non-empty string"
        )
    return value


def _payload_path(payload: Mapping[str, object], name: str) -> Path:
    value = _payload_string(payload, name)
    path = Path(value)
    if not path.is_absolute():
        raise PluginContextError(
            f"pluginContext.{name} must be an absolute path: {value!r}"
        )
    return path


@dataclass(frozen=True, slots=True)
class PluginContext:
    """Immutable identity, session, path, and capability data for one plugin."""

    id: str
    session_id: str
    generation: int
    plugin_dir: Path
    data_dir: Path
    cache_dir: Path
    temp_dir: Path
    capabilities: frozenset[str]

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise PluginContextError("plugin id must not be empty")
        if not isinstance(self.session_id, str) or not self.session_id.strip():
            raise PluginContextError("plugin session id must not be empty")
        if (
            isinstance(self.generation, bool)
            or not isinstance(self.generation, int)
            or self.generation < 1
        ):
            raise PluginContextError("plugin generation must be positive")
        for name in ("plugin_dir", "data_dir", "cache_dir", "temp_dir"):
            path = getattr(self, name)
            if not isinstance(path, Path) or not path.is_absolute():
                raise PluginContextError(f"{name} must be an absolute path")
        object.__setattr__(
            self,
            "capabilities",
            _capability_set(self.capabilities, "plugin capabilities"),
        )

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str],
        *,
        allow_standalone: bool = False,
    ) -> PluginContext:
        source = environment
        present = [name for name in PLUGIN_CONTEXT_ENV_VARS if name in source]
        if not present:
            if allow_standalone:
                return cls.standalone()
            raise PluginContextError(
                "Missing plugin startup context: "
                + ", ".join(PLUGIN_CONTEXT_ENV_VARS)
            )

        missing = [name for name in PLUGIN_CONTEXT_ENV_VARS if name not in source]
        if missing:
            raise PluginContextError(
                "Incomplete plugin startup context; missing: " + ", ".join(missing)
            )

        generation_value = _required_value(source, PLUGIN_GENERATION_ENV)
        try:
            generation = int(generation_value)
        except ValueError as error:
            raise PluginContextError(
                f"{PLUGIN_GENERATION_ENV} must be an integer"
            ) from error

        capabilities_value = _required_value(source, PLUGIN_CAPABILITIES_ENV)
        try:
            capabilities = json.loads(capabilities_value)
        except json.JSONDecodeError as error:
            raise PluginContextError(
                f"{PLUGIN_CAPABILITIES_ENV} must be valid JSON"
            ) from error

        return cls(
            id=_required_value(source, PLUGIN_ID_ENV),
            session_id=_required_value(source, PLUGIN_SESSION_ID_ENV),
            generation=generation,
            plugin_dir=_absolute_path(source, PLUGIN_DIR_ENV),
            data_dir=_absolute_path(source, PLUGIN_DATA_DIR_ENV),
            cache_dir=_absolute_path(source, PLUGIN_CACHE_DIR_ENV),
            temp_dir=_absolute_path(source, PLUGIN_TEMP_DIR_ENV),
            capabilities=_capability_set(
                capabilities,
                PLUGIN_CAPABILITIES_ENV,
            ),
        )

    @classmethod
    def standalone(cls, root: Path | None = None) -> PluginContext:
        root = Path.cwd().resolve() if root is None else root.resolve()
        return cls(
            id="standalone",
            session_id="standalone",
            generation=1,
            plugin_dir=root,
            data_dir=root / "data",
            cache_dir=root / "cache",
            temp_dir=root / "temp",
            capabilities=frozenset(),
        )

    @classmethod
    def from_handshake_payload(cls, payload: object) -> PluginContext:
        if not isinstance(payload, Mapping):
            raise PluginContextError("ide.initialize pluginContext is required")
        generation = payload.get("generation")
        if isinstance(generation, bool) or not isinstance(generation, int):
            raise PluginContextError(
                "pluginContext.generation must be an integer"
            )
        return cls(
            id=_payload_string(payload, "id"),
            session_id=_payload_string(payload, "session"),
            generation=generation,
            plugin_dir=_payload_path(payload, "pluginDir"),
            data_dir=_payload_path(payload, "dataDir"),
            cache_dir=_payload_path(payload, "cacheDir"),
            temp_dir=_payload_path(payload, "tempDir"),
            capabilities=_capability_set(
                payload.get("capabilities"),
                "pluginContext.capabilities",
            ),
        )

    def with_handshake(
        self,
        *,
        session_id: str,
        generation: int,
        capabilities: Iterable[str],
    ) -> PluginContext:
        return replace(
            self,
            session_id=session_id,
            generation=generation,
            capabilities=_capability_set(
                capabilities,
                "handshake capabilities",
            ),
        )

    @property
    def plugin_id(self) -> str:
        return self.id

    @property
    def session(self) -> str:
        return self.session_id

    @property
    def sessionId(self) -> str:
        return self.session_id

    @property
    def pluginDir(self) -> Path:
        return self.plugin_dir

    @property
    def dataDir(self) -> Path:
        return self.data_dir

    @property
    def cacheDir(self) -> Path:
        return self.cache_dir

    @property
    def tempDir(self) -> Path:
        return self.temp_dir
