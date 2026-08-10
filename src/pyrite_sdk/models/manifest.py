from __future__ import annotations

import math
import re
import tomllib
from enum import StrEnum
from pathlib import Path
from typing import Any, Iterable, Mapping, NoReturn, Sequence, TypeGuard

from pydantic import BaseModel, ConfigDict, Field, ValidationError


_MIN_INT64 = -(1 << 63)
_MAX_INT64 = (1 << 63) - 1


def _is_int64(value: Any) -> TypeGuard[int]:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and _MIN_INT64 <= value <= _MAX_INT64
    )


def _is_json_value(value: Any) -> bool:
    if value is None or isinstance(value, (str, bool)):
        return True
    if _is_int64(value):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, list):
        return all(_is_json_value(item) for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and _is_json_value(item)
            for key, item in value.items()
        )
    return False


def _is_blank(value: str) -> bool:
    return not value.replace("\ufeff", "").strip()


def _utf16_code_unit_length(value: str) -> int:
    return len(value.encode("utf-16-le", "surrogatepass")) // 2


def _json_values_equal(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left == right
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            _json_values_equal(left_item, right_item)
            for left_item, right_item in zip(left, right, strict=True)
        )
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        return left.keys() == right.keys() and all(
            _json_values_equal(left[key], right[key]) for key in left
        )
    return type(left) is type(right) and left == right


class PluginType(StrEnum):
    UI = "ui"
    SERVICE = "service"
    DATA = "data"


class PluginManifestErrorCode:
    MISSING_MANIFEST = "manifest_missing"
    INVALID_TOML = "manifest_invalid_toml"
    MISSING_VERSION = "manifest_missing_version"
    UNSUPPORTED_VERSION = "manifest_unsupported_version"
    INVALID_SCHEMA = "manifest_invalid_schema"
    INVALID_PLUGIN_ID = "manifest_invalid_plugin_id"
    INVALID_PERMISSION = "manifest_invalid_permission"
    INVALID_CONTRIBUTION_ID = "manifest_invalid_contribution_id"
    CONTRIBUTION_CONFLICT = "manifest_contribution_conflict"
    MISSING_NAVIGATION_CONTAINER = "manifest_missing_navigation_container"
    UNKNOWN_RENDERER = "manifest_unknown_renderer"
    RFW_RENDERER_UNSUPPORTED = "manifest_rfw_renderer_unsupported"
    INVALID_WHEN = "manifest_invalid_when"
    UNKNOWN_ICON = "manifest_unknown_icon"
    INVALID_ACTIVATION_EVENT = "manifest_invalid_activation_event"


class ManifestValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def __str__(self) -> str:
        return f"ManifestValidationError({self.code}): {self.message}"


class _ManifestModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        strict=True,
    )


class PluginIconReference(_ManifestModel):
    material: str | None = None
    asset: str | None = None


class PluginIconSet(_ManifestModel):
    full: str
    monochrome: str


class PluginNavigationContainerContribution(_ManifestModel):
    id: str
    title: str
    icon: PluginIconReference | None = None
    location: str = "primary"
    order: int = 0
    when: str | None = None


class PluginViewContribution(_ManifestModel):
    id: str
    container: str
    title: str
    renderer: str
    icon: PluginIconReference | None = None
    order: int = 0
    when: str | None = None


class PluginCommandContribution(_ManifestModel):
    id: str
    title: str
    icon: PluginIconReference | None = None
    order: int = 0
    when: str | None = None


class PluginMenuContribution(_ManifestModel):
    location: str
    command: str
    view: str | None = None
    group: str | None = None
    order: int = 0
    when: str | None = None


class PluginConfigurationContribution(_ManifestModel):
    id: str
    title: str
    type: str
    description: str = ""
    default_value: Any = Field(default=None, alias="default")
    enum_values: list[Any] = Field(default_factory=list, alias="enum")
    order: int = 0
    when: str | None = None


class PluginContributions(_ManifestModel):
    navigation_containers: list[PluginNavigationContainerContribution] = Field(
        default_factory=list
    )
    views: list[PluginViewContribution] = Field(default_factory=list)
    commands: list[PluginCommandContribution] = Field(default_factory=list)
    menus: list[PluginMenuContribution] = Field(default_factory=list)
    configuration: list[PluginConfigurationContribution] = Field(
        default_factory=list
    )

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(
            contribution.id
            for contributions in (
                self.navigation_containers,
                self.views,
                self.commands,
                self.configuration,
            )
            for contribution in contributions
        )


class PluginManifestV2(_ManifestModel):
    manifest_version: int = 2
    id: str
    name: str
    version: str
    type: PluginType = Field(strict=False)
    protocol_version: int = 1
    python_version: str | None = None
    author: str = ""
    description: str = ""
    icons: PluginIconSet | None = None
    activation_events: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    platforms: list[str] = Field(default_factory=list)
    contributes: PluginContributions = Field(default_factory=PluginContributions)

    @property
    def permissions_by_resource(self) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        for permission in self.permissions:
            resource, separator, action = permission.partition(".")
            if separator and resource and action:
                result.setdefault(resource, []).append(action)
        return result

    @property
    def auto_start(self) -> bool:
        return "onStartup" in self.activation_events


class PluginManifestValidator:
    DEFAULT_RENDERERS = frozenset(
        {
            "native.tree",
            "native.virtualList",
            "native.table",
            "native.form",
            "native.markdown",
            "native.log",
            "native.outline",
            "native.variableInspector",
        }
    )
    DEFAULT_ICONS: frozenset[str] | None = None
    DEFAULT_CONTEXT_KEYS = frozenset(
        {
            "editor.language",
            "editor.hasDocument",
            "runtime.language",
            "runtime.state",
            "device.connected",
            "workspace.opened",
            "plugin.enabled",
            "view.active",
        }
    )
    SUPPORTED_PERMISSIONS = frozenset(
        {
            "ui.view",
            "ui.navigate",
            "ui.notify",
            "file.read",
            "file.write",
            "board.read",
            "board.write",
            "editor.read",
            "editor.write",
            "persistence.read",
            "persistence.write",
            "tab.create",
            "tab.manage",
            "settings.read",
            "settings.write",
            "serial.read",
            "serial.write",
            "data.read",
            "data.write",
            "dialog.show",
            "runtime.inspect",
        }
    )
    SUPPORTED_PLATFORMS = frozenset({"windows", "linux", "macos", "android"})
    NAVIGATION_LOCATIONS = frozenset({"primary", "secondary"})
    MENU_LOCATIONS = frozenset(
        {"view/title", "view/context", "navigation/context", "commandPalette"}
    )
    CONFIGURATION_TYPES = frozenset(
        {"string", "integer", "number", "boolean", "array"}
    )

    _PLUGIN_ID_PATTERN = re.compile(
        r"^[A-Za-z0-9][A-Za-z0-9_-]*(?:\.[A-Za-z0-9][A-Za-z0-9_-]*)*$"
    )
    _CONTRIBUTION_ID_PATTERN = re.compile(
        r"^[A-Za-z0-9][A-Za-z0-9_-]*(?:\.[A-Za-z0-9][A-Za-z0-9_-]*)+$"
    )
    _LANGUAGE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_+.-]*$")
    _WINDOWS_RESERVED_PLUGIN_ID = re.compile(
        r"^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)",
        re.IGNORECASE,
    )

    def __init__(
        self,
        *,
        supported_renderers: Iterable[str] | None = None,
        supported_icons: Iterable[str] | None = None,
        context_keys: Iterable[str] | None = None,
    ) -> None:
        self.supported_renderers = frozenset(
            self.DEFAULT_RENDERERS
            if supported_renderers is None
            else supported_renderers
        )
        if supported_icons is None:
            from ..api.material_icons import MATERIAL_ICON_CODES

            supported_icons = MATERIAL_ICON_CODES
        self.supported_icons = frozenset(supported_icons)
        self.context_keys = frozenset(
            self.DEFAULT_CONTEXT_KEYS if context_keys is None else context_keys
        )

    def validate(self, manifest: PluginManifestV2) -> PluginManifestV2:
        if not _is_int64(manifest.manifest_version):
            self._raise(
                PluginManifestErrorCode.INVALID_SCHEMA,
                "manifest_version must fit in a signed 64-bit integer",
            )
        if manifest.manifest_version != 2:
            self._raise(
                PluginManifestErrorCode.UNSUPPORTED_VERSION,
                f"Unsupported manifest version: {manifest.manifest_version}",
            )
        if (
            self._PLUGIN_ID_PATTERN.fullmatch(manifest.id) is None
            or self._WINDOWS_RESERVED_PLUGIN_ID.match(manifest.id) is not None
        ):
            self._raise(
                PluginManifestErrorCode.INVALID_PLUGIN_ID,
                f"Invalid plugin ID: {manifest.id}",
            )
        if _is_blank(manifest.name) or _is_blank(manifest.version):
            self._raise(
                PluginManifestErrorCode.INVALID_SCHEMA,
                "Plugin name and version must not be empty",
            )
        if not _is_int64(manifest.protocol_version):
            self._raise(
                PluginManifestErrorCode.INVALID_SCHEMA,
                "protocol_version must fit in a signed 64-bit integer",
            )
        if manifest.protocol_version != 1:
            self._raise(
                PluginManifestErrorCode.INVALID_SCHEMA,
                f"Unsupported plugin protocol version: {manifest.protocol_version}",
            )
        if manifest.icons is not None:
            self._validate_asset_path(manifest.icons.full, "icons.full")
            self._validate_asset_path(
                manifest.icons.monochrome, "icons.monochrome"
            )

        self._validate_unique_strings(
            manifest.permissions,
            PluginManifestErrorCode.INVALID_PERMISSION,
            "permission",
        )
        for permission in manifest.permissions:
            if permission not in self.SUPPORTED_PERMISSIONS:
                self._raise(
                    PluginManifestErrorCode.INVALID_PERMISSION,
                    f"Unsupported permission: {permission}",
                )

        self._validate_unique_strings(
            manifest.platforms,
            PluginManifestErrorCode.INVALID_SCHEMA,
            "platform",
        )
        for platform in manifest.platforms:
            if platform not in self.SUPPORTED_PLATFORMS:
                self._raise(
                    PluginManifestErrorCode.INVALID_SCHEMA,
                    f"Unsupported platform: {platform}",
                )

        contributions = manifest.contributes
        if (
            manifest.type == PluginType.UI
            and not contributions.navigation_containers
        ):
            self._raise(
                PluginManifestErrorCode.MISSING_NAVIGATION_CONTAINER,
                "UI plugins must declare a navigation container",
            )

        ids: dict[str, str] = {}

        def register_id(
            contribution_id: str,
            kind: str,
            *,
            allow_plugin_id: bool = False,
        ) -> None:
            valid_prefix = contribution_id.startswith(f"{manifest.id}.") or (
                allow_plugin_id and contribution_id == manifest.id
            )
            if not valid_prefix or (
                contribution_id != manifest.id
                and self._CONTRIBUTION_ID_PATTERN.fullmatch(contribution_id) is None
            ):
                self._raise(
                    PluginManifestErrorCode.INVALID_CONTRIBUTION_ID,
                    f"{kind} ID must use the {manifest.id} namespace: "
                    f"{contribution_id}",
                )
            normalized = contribution_id.lower()
            previous = ids.get(normalized)
            if previous is not None:
                self._raise(
                    PluginManifestErrorCode.CONTRIBUTION_CONFLICT,
                    f"Contribution ID {contribution_id} conflicts with {previous}",
                )
            ids[normalized] = f"{kind} {contribution_id}"

        for container in contributions.navigation_containers:
            register_id(
                container.id,
                "navigation container",
                allow_plugin_id=True,
            )
            self._require_text(container.title, "navigation container title")
            self._validate_order(container.order, "navigation container")
            if container.location not in self.NAVIGATION_LOCATIONS:
                self._raise(
                    PluginManifestErrorCode.INVALID_SCHEMA,
                    f"Unsupported navigation location: {container.location}",
                )
            self._validate_icon(container.icon)
            self._validate_when(container.when)

        for view in contributions.views:
            register_id(view.id, "view")
            self._require_text(view.title, "view title")
            self._validate_order(view.order, "view")
            self._validate_renderer(view.renderer)
            self._validate_icon(view.icon)
            self._validate_when(view.when)

        for command in contributions.commands:
            register_id(command.id, "command")
            self._require_text(command.title, "command title")
            self._validate_order(command.order, "command")
            self._validate_icon(command.icon)
            self._validate_when(command.when)

        for configuration in contributions.configuration:
            register_id(configuration.id, "configuration")
            self._require_text(configuration.title, "configuration title")
            self._validate_order(configuration.order, "configuration")
            self._validate_configuration(configuration)
            self._validate_when(configuration.when)

        navigation_ids = {
            contribution.id for contribution in contributions.navigation_containers
        }
        view_ids = {contribution.id for contribution in contributions.views}
        command_ids = {contribution.id for contribution in contributions.commands}

        for view in contributions.views:
            if view.container not in navigation_ids:
                self._raise(
                    PluginManifestErrorCode.INVALID_SCHEMA,
                    f"View {view.id} references an unknown container: "
                    f"{view.container}",
                )

        for menu in contributions.menus:
            self._validate_order(menu.order, "menu")
            if menu.location not in self.MENU_LOCATIONS:
                self._raise(
                    PluginManifestErrorCode.INVALID_SCHEMA,
                    f"Unsupported menu location: {menu.location}",
                )
            if menu.command not in command_ids:
                self._raise(
                    PluginManifestErrorCode.INVALID_SCHEMA,
                    f"Menu references an unknown command: {menu.command}",
                )
            if menu.view is not None and menu.view not in view_ids:
                self._raise(
                    PluginManifestErrorCode.INVALID_SCHEMA,
                    f"Menu references an unknown view: {menu.view}",
                )
            self._validate_when(menu.when)

        self._validate_activation_events(manifest, view_ids, command_ids)
        return manifest

    def validate_no_conflicts(
        self,
        candidate: PluginManifestV2,
        installed: Iterable[PluginManifestV2],
    ) -> None:
        candidate_ids = {
            contribution_id.lower(): contribution_id
            for contribution_id in candidate.contributes.ids
        }
        for manifest in installed:
            if manifest.id == candidate.id:
                continue
            if manifest.id.lower() == candidate.id.lower():
                self._raise(
                    PluginManifestErrorCode.CONTRIBUTION_CONFLICT,
                    f"Plugin ID {candidate.id} conflicts with plugin {manifest.id}",
                )
            for contribution_id in manifest.contributes.ids:
                candidate_id = candidate_ids.get(contribution_id.lower())
                if candidate_id is not None:
                    self._raise(
                        PluginManifestErrorCode.CONTRIBUTION_CONFLICT,
                        f"Contribution ID {candidate_id} conflicts with plugin "
                        f"{manifest.id}",
                    )

    def _validate_renderer(self, renderer: str) -> None:
        normalized = renderer.lower()
        if normalized == "rfw" or normalized.startswith("rfw."):
            self._raise(
                PluginManifestErrorCode.RFW_RENDERER_UNSUPPORTED,
                f"RFW renderer is not supported: {renderer}",
            )
        if renderer not in self.supported_renderers:
            self._raise(
                PluginManifestErrorCode.UNKNOWN_RENDERER,
                f"Unsupported renderer: {renderer}",
            )

    def _validate_icon(self, icon: PluginIconReference | None) -> None:
        if icon is None:
            return
        sources = [icon.material is not None, icon.asset is not None]
        if sum(sources) != 1:
            self._raise(
                PluginManifestErrorCode.INVALID_SCHEMA,
                "Icon references must contain exactly one source",
            )
        if icon.material is not None:
            if icon.material not in self.supported_icons:
                self._raise(
                    PluginManifestErrorCode.UNKNOWN_ICON,
                    f"Unsupported Material icon: {icon.material}",
                )
            return
        self._validate_asset_path(icon.asset or "", "icon.asset")

    @classmethod
    def _validate_asset_path(cls, value: str, field: str) -> None:
        normalized = value.replace("\\", "/")
        parts = normalized.split("/")
        if (
            not value
            or value != normalized
            or not normalized.startswith("assets/")
            or normalized.startswith("/")
            or ".." in parts
            or "\x00" in normalized
            or re.match(r"^[A-Za-z]:", normalized)
        ):
            cls._raise(
                PluginManifestErrorCode.INVALID_SCHEMA,
                f"{field} must be a relative path below assets/",
            )

    def _validate_when(self, expression: str | None) -> None:
        if expression is None:
            return
        try:
            _WhenExpressionParser(expression, self.context_keys).parse()
        except _WhenFormatError as error:
            self._raise(
                PluginManifestErrorCode.INVALID_WHEN,
                f"Invalid when expression: {error}",
            )

    def _validate_activation_events(
        self,
        manifest: PluginManifestV2,
        view_ids: set[str],
        command_ids: set[str],
    ) -> None:
        self._validate_unique_strings(
            manifest.activation_events,
            PluginManifestErrorCode.INVALID_ACTIVATION_EVENT,
            "activation event",
        )
        for event in manifest.activation_events:
            if event == "onStartup":
                continue
            kind, separator, target = event.partition(":")
            if not separator or not kind or not target:
                self._raise(
                    PluginManifestErrorCode.INVALID_ACTIVATION_EVENT,
                    f"Unsupported activation event: {event}",
                )
            valid = (
                (kind == "onView" and target in view_ids)
                or (kind == "onCommand" and target in command_ids)
                or (
                    kind == "onLanguage"
                    and self._LANGUAGE_PATTERN.fullmatch(target) is not None
                )
            )
            if not valid:
                self._raise(
                    PluginManifestErrorCode.INVALID_ACTIVATION_EVENT,
                    f"Invalid activation event: {event}",
                )

    def _validate_configuration(
        self,
        configuration: PluginConfigurationContribution,
    ) -> None:
        if configuration.type not in self.CONFIGURATION_TYPES:
            self._raise(
                PluginManifestErrorCode.INVALID_SCHEMA,
                f"Unsupported configuration type: {configuration.type}",
            )
        if not _is_json_value(configuration.default_value):
            self._raise(
                PluginManifestErrorCode.INVALID_SCHEMA,
                f"Configuration {configuration.id} has a non-JSON default value",
            )
        if not self._matches_configuration_type(
            configuration.type,
            configuration.default_value,
        ):
            self._raise(
                PluginManifestErrorCode.INVALID_SCHEMA,
                f"Configuration {configuration.id} has an invalid default value",
            )
        for value in configuration.enum_values:
            if not _is_json_value(value):
                self._raise(
                    PluginManifestErrorCode.INVALID_SCHEMA,
                    f"Configuration {configuration.id} has a non-JSON enum value",
                )
            if value is None or not self._matches_configuration_type(
                configuration.type, value
            ):
                self._raise(
                    PluginManifestErrorCode.INVALID_SCHEMA,
                    f"Configuration {configuration.id} has an invalid enum value",
                )
        if (
            configuration.default_value is not None
            and configuration.enum_values
            and not any(
                _json_values_equal(value, configuration.default_value)
                for value in configuration.enum_values
            )
        ):
            self._raise(
                PluginManifestErrorCode.INVALID_SCHEMA,
                f"Configuration {configuration.id} default is not in its enum",
            )

    @staticmethod
    def _matches_configuration_type(configuration_type: str, value: Any) -> bool:
        if value is None:
            return True
        if configuration_type == "string":
            return isinstance(value, str)
        if configuration_type == "integer":
            return _is_int64(value)
        if configuration_type == "number":
            return (_is_int64(value)) or (
                isinstance(value, float) and math.isfinite(value)
            )
        if configuration_type == "boolean":
            return isinstance(value, bool)
        if configuration_type == "array":
            return isinstance(value, list) and all(
                _is_json_value(item) for item in value
            )
        return False

    @classmethod
    def _validate_order(cls, value: int, contribution: str) -> None:
        if not _is_int64(value):
            cls._raise(
                PluginManifestErrorCode.INVALID_SCHEMA,
                f"{contribution} order must fit in a signed 64-bit integer",
            )

    @classmethod
    def _require_text(cls, value: str, field: str) -> None:
        if _is_blank(value):
            cls._raise(
                PluginManifestErrorCode.INVALID_SCHEMA,
                f"{field} must not be empty",
            )

    @classmethod
    def _validate_unique_strings(
        cls,
        values: Sequence[str],
        code: str,
        label: str,
    ) -> None:
        seen: set[str] = set()
        for value in values:
            if value in seen:
                cls._raise(code, f"Duplicate {label}: {value}")
            seen.add(value)

    @staticmethod
    def _raise(code: str, message: str) -> None:
        raise ManifestValidationError(code, message)


_TOP_LEVEL_FIELDS = frozenset(
    {
        "manifest_version",
        "id",
        "name",
        "version",
        "type",
        "protocol_version",
        "python_version",
        "author",
        "description",
        "icons",
        "activation_events",
        "permissions",
        "platforms",
        "contributes",
    }
)

_CONTRIBUTION_FIELDS = {
    "navigation_containers": frozenset(
        {"id", "title", "icon", "location", "order", "when"}
    ),
    "views": frozenset(
        {"id", "container", "title", "renderer", "icon", "order", "when"}
    ),
    "commands": frozenset({"id", "title", "icon", "order", "when"}),
    "menus": frozenset(
        {"location", "command", "view", "group", "order", "when"}
    ),
    "configuration": frozenset(
        {"id", "title", "type", "description", "default", "enum", "order", "when"}
    ),
}

_REQUIRED_CONTRIBUTION_STRINGS = {
    "navigation_containers": ("id", "title"),
    "views": ("id", "container", "title", "renderer"),
    "commands": ("id", "title"),
    "menus": ("location", "command"),
    "configuration": ("id", "title", "type"),
}

_OPTIONAL_CONTRIBUTION_STRINGS = {
    "navigation_containers": ("location", "when"),
    "views": ("when",),
    "commands": ("when",),
    "menus": ("view", "group", "when"),
    "configuration": ("description", "when"),
}


def load_toml(
    contents: str | bytes,
    *,
    validator: PluginManifestValidator | None = None,
) -> PluginManifestV2:
    try:
        source = contents.decode("utf-8") if isinstance(contents, bytes) else contents
        raw = tomllib.loads(source)
    except (UnicodeDecodeError, tomllib.TOMLDecodeError, RecursionError) as error:
        raise ManifestValidationError(
            PluginManifestErrorCode.INVALID_TOML,
            f"Invalid plugin.toml: {error}",
        ) from error

    try:
        _validate_toml_shape(raw)
        return _model_from_mapping(raw, validator=validator)
    except RecursionError as error:
        raise ManifestValidationError(
            PluginManifestErrorCode.INVALID_TOML,
            "Invalid plugin.toml: manifest nesting is too deep",
        ) from error


def load_file(
    path: str | Path,
    *,
    validator: PluginManifestValidator | None = None,
) -> PluginManifestV2:
    manifest_path = Path(path)
    if not manifest_path.is_file():
        raise ManifestValidationError(
            PluginManifestErrorCode.MISSING_MANIFEST,
            "plugin.toml is missing",
        )
    try:
        contents = manifest_path.read_bytes()
    except OSError as error:
        raise ManifestValidationError(
            PluginManifestErrorCode.INVALID_TOML,
            f"Unable to read plugin.toml: {error}",
        ) from error
    manifest = load_toml(contents, validator=validator)
    _validate_manifest_asset_files(manifest_path.parent, manifest)
    return manifest


def _validate_manifest_asset_files(
    plugin_dir: Path, manifest: PluginManifestV2
) -> None:
    assets: list[str] = []
    if manifest.icons is not None:
        assets.extend((manifest.icons.full, manifest.icons.monochrome))
    for contribution in (
        *manifest.contributes.navigation_containers,
        *manifest.contributes.views,
        *manifest.contributes.commands,
    ):
        if contribution.icon is not None and contribution.icon.asset is not None:
            assets.append(contribution.icon.asset)
    root = plugin_dir.resolve()
    for asset in assets:
        candidate = (root / asset).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as error:
            raise ManifestValidationError(
                PluginManifestErrorCode.INVALID_SCHEMA,
                f"Declared plugin asset escapes the plugin directory: {asset}",
            ) from error
        if not candidate.is_file() or candidate.is_symlink():
            raise ManifestValidationError(
                PluginManifestErrorCode.INVALID_SCHEMA,
                f"Declared plugin asset is missing or invalid: {asset}",
            )


def build_manifest(
    *,
    plugin_id: str,
    name: str,
    version: str,
    plugin_type: PluginType | str,
    python_version: str | None = None,
    author: str = "",
    description: str = "",
    icons: PluginIconSet | None = None,
    activation_events: Iterable[str] = (),
    permissions: Iterable[str] = (),
    platforms: Iterable[str] = (),
    contributes: PluginContributions | None = None,
    validator: PluginManifestValidator | None = None,
) -> PluginManifestV2:
    data = {
        "manifest_version": 2,
        "id": plugin_id,
        "name": name,
        "version": version,
        "type": plugin_type,
        "protocol_version": 1,
        "python_version": python_version,
        "author": author,
        "description": description,
        "icons": icons,
        "activation_events": list(activation_events),
        "permissions": list(permissions),
        "platforms": list(platforms),
        "contributes": contributes or PluginContributions(),
    }
    return _model_from_mapping(data, validator=validator)


def _model_from_mapping(
    raw: Mapping[str, Any],
    *,
    validator: PluginManifestValidator | None,
) -> PluginManifestV2:
    try:
        manifest = PluginManifestV2.model_validate(raw)
    except (ValidationError, RecursionError) as error:
        raise ManifestValidationError(
            PluginManifestErrorCode.INVALID_SCHEMA,
            f"Invalid manifest schema: {error}",
        ) from error
    return (validator or PluginManifestValidator()).validate(manifest)


def _validate_toml_shape(raw: Mapping[str, Any]) -> None:
    if "manifest_version" not in raw:
        raise ManifestValidationError(
            PluginManifestErrorCode.MISSING_VERSION,
            "manifest_version is required",
        )
    manifest_version = _required_int(raw, "manifest_version", "manifest")
    if manifest_version != 2:
        raise ManifestValidationError(
            PluginManifestErrorCode.UNSUPPORTED_VERSION,
            f"Unsupported manifest version: {manifest_version}",
        )
    _reject_unknown_fields(raw, _TOP_LEVEL_FIELDS, "manifest")

    for key in ("id", "name", "version", "type"):
        _required_string(raw, key, "manifest")
    _required_int(raw, "protocol_version", "manifest")
    for key in ("python_version", "author", "description"):
        _optional_string(raw, key, "manifest")
    icons = raw.get("icons")
    if icons is not None:
        if not isinstance(icons, Mapping):
            _schema_error("manifest.icons must be a table")
        _reject_unknown_fields(icons, frozenset({"full", "monochrome"}), "icons")
        _required_string(icons, "full", "icons")
        _required_string(icons, "monochrome", "icons")
    for key in ("activation_events", "permissions", "platforms"):
        _string_list(raw, key, "manifest")

    contributes = raw.get("contributes", {})
    if not isinstance(contributes, Mapping):
        _schema_error("manifest.contributes must be a table")
    _reject_unknown_fields(
        contributes,
        frozenset(_CONTRIBUTION_FIELDS),
        "contributes",
    )
    for kind, fields in _CONTRIBUTION_FIELDS.items():
        entries = contributes.get(kind, [])
        if not isinstance(entries, list):
            _schema_error(f"contributes.{kind} must be an array of tables")
        for index, entry in enumerate(entries):
            path = f"contributes.{kind}[{index}]"
            if not isinstance(entry, Mapping):
                _schema_error(f"{path} must be a table")
            _reject_unknown_fields(entry, fields, path)
            for key in _REQUIRED_CONTRIBUTION_STRINGS[kind]:
                _required_string(entry, key, path)
            for key in _OPTIONAL_CONTRIBUTION_STRINGS[kind]:
                if key == "when":
                    _optional_expression(entry, key, path)
                else:
                    _optional_string(entry, key, path)
            icon = entry.get("icon")
            if icon is not None:
                if not isinstance(icon, Mapping):
                    _schema_error(f"{path}.icon must be a table")
                _reject_unknown_fields(
                    icon, frozenset({"material", "asset"}), f"{path}.icon"
                )
                if len(icon) != 1:
                    _schema_error(
                        f"{path}.icon must contain exactly one source"
                    )
                key = "material" if "material" in icon else "asset"
                _required_string(icon, key, f"{path}.icon")
            _optional_int(entry, "order", path)
            if kind == "configuration":
                enum_values = entry.get("enum")
                if enum_values is not None and not isinstance(enum_values, list):
                    _schema_error(f"{path}.enum must be an array")


def _reject_unknown_fields(
    table: Mapping[str, Any],
    fields: frozenset[str],
    path: str,
) -> None:
    for key in table:
        if key not in fields:
            _schema_error(f"Unknown field: {path}.{key}")


def _required_string(table: Mapping[str, Any], key: str, path: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or _is_blank(value):
        _schema_error(f"{path}.{key} must be a non-empty string")
    return value


def _optional_string(
    table: Mapping[str, Any],
    key: str,
    path: str,
) -> str | None:
    value = table.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or _is_blank(value):
        _schema_error(f"{path}.{key} must be a non-empty string")
    return value


def _optional_expression(
    table: Mapping[str, Any],
    key: str,
    path: str,
) -> str | None:
    value = table.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        _schema_error(f"{path}.{key} must be a string")
    return value


def _required_int(table: Mapping[str, Any], key: str, path: str) -> int:
    value = table.get(key)
    if not _is_int64(value):
        _schema_error(f"{path}.{key} must be a signed 64-bit integer")
    return value


def _optional_int(table: Mapping[str, Any], key: str, path: str) -> int | None:
    value = table.get(key)
    if value is None:
        return None
    if not _is_int64(value):
        _schema_error(f"{path}.{key} must be a signed 64-bit integer")
    return value


def _string_list(table: Mapping[str, Any], key: str, path: str) -> list[str]:
    value = table.get(key)
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        _schema_error(f"{path}.{key} must be an array of strings")
    return value


def _schema_error(message: str) -> NoReturn:
    raise ManifestValidationError(PluginManifestErrorCode.INVALID_SCHEMA, message)


class _WhenFormatError(ValueError):
    def __init__(self, message: str, offset: int | None = None) -> None:
        suffix = "" if offset is None else f" at offset {offset}"
        super().__init__(f"{message}{suffix}")


class _WhenExpressionParser:
    _MAX_SOURCE_LENGTH = 4096
    _MAX_TOKENS = 256
    _MAX_DEPTH = 64
    _IDENTIFIER = "identifier"
    _LITERAL = "literal"
    _AND = "and"
    _OR = "or"
    _NOT = "not"
    _EQUAL = "equal"
    _NOT_EQUAL = "not_equal"
    _LEFT_PARENTHESIS = "left_parenthesis"
    _RIGHT_PARENTHESIS = "right_parenthesis"
    _END = "end"

    def __init__(self, source: str, context_keys: frozenset[str]) -> None:
        self.source = source
        self.context_keys = context_keys
        self.tokens = self._tokenize(source)
        self.index = 0
        self.depth = 0

    def parse(self) -> None:
        if not self.source.strip():
            raise _WhenFormatError("expression is empty")
        self._parse_or()
        self._expect(self._END, "unexpected trailing input")

    def _parse_or(self) -> None:
        self._parse_and()
        while self._match(self._OR):
            self._parse_and()

    def _parse_and(self) -> None:
        self._parse_unary()
        while self._match(self._AND):
            self._parse_unary()

    def _parse_unary(self) -> None:
        if self.depth >= self._MAX_DEPTH:
            raise _WhenFormatError("expression is too deeply nested")
        self.depth += 1
        try:
            if self._match(self._NOT):
                self._parse_unary()
                return
            if self._match(self._LEFT_PARENTHESIS):
                self._parse_or()
                self._expect(self._RIGHT_PARENTHESIS, "missing closing parenthesis")
                return
            self._parse_predicate()
        finally:
            self.depth -= 1

    def _parse_predicate(self) -> None:
        identifier = self._expect(self._IDENTIFIER, "expected a context key")
        if identifier[1] not in self.context_keys:
            raise _WhenFormatError(
                f"unknown context key {identifier[1]}",
                identifier[2],
            )
        if self._match(self._EQUAL) or self._match(self._NOT_EQUAL):
            self._expect(self._LITERAL, "expected a literal value")

    def _match(self, token_type: str) -> bool:
        if self.tokens[self.index][0] != token_type:
            return False
        self.index += 1
        return True

    def _expect(self, token_type: str, message: str) -> tuple[str, str, int]:
        token = self.tokens[self.index]
        if token[0] != token_type:
            raise _WhenFormatError(message, token[2])
        self.index += 1
        return token

    def _tokenize(self, source: str) -> list[tuple[str, str, int]]:
        if _utf16_code_unit_length(source) > self._MAX_SOURCE_LENGTH:
            raise _WhenFormatError("expression is too long")
        tokens: list[tuple[str, str, int]] = []
        index = 0
        while index < len(source):
            character = source[index]
            if character in " \t\n\r":
                index += 1
                continue
            if len(tokens) >= self._MAX_TOKENS:
                raise _WhenFormatError("expression is too complex", index)
            operators = {
                "&&": self._AND,
                "||": self._OR,
                "==": self._EQUAL,
                "!=": self._NOT_EQUAL,
            }
            operator = source[index : index + 2]
            if operator in operators:
                tokens.append((operators[operator], operator, index))
                index += 2
                continue
            single_tokens = {
                "!": self._NOT,
                "(": self._LEFT_PARENTHESIS,
                ")": self._RIGHT_PARENTHESIS,
            }
            if character in single_tokens:
                tokens.append((single_tokens[character], character, index))
                index += 1
                continue
            if character in {'"', "'"}:
                start = index
                quote = character
                index += 1
                closed = False
                while index < len(source):
                    current = source[index]
                    if current == "\\":
                        index += 2
                        continue
                    if current == quote:
                        index += 1
                        closed = True
                        break
                    if current in "\n\r":
                        break
                    index += 1
                if not closed:
                    raise _WhenFormatError("unterminated string literal", start)
                tokens.append((self._LITERAL, source[start:index], start))
                continue
            if character.isascii() and (
                character.isdigit()
                or (
                    character == "-"
                    and index + 1 < len(source)
                    and source[index + 1].isascii()
                    and source[index + 1].isdigit()
                )
            ):
                start = index
                index += 1
                while (
                    index < len(source)
                    and source[index].isascii()
                    and source[index].isdigit()
                ):
                    index += 1
                if index < len(source) and source[index] == ".":
                    index += 1
                    fraction_start = index
                    while (
                        index < len(source)
                        and source[index].isascii()
                        and source[index].isdigit()
                    ):
                        index += 1
                    if index == fraction_start:
                        raise _WhenFormatError("invalid number literal", start)
                tokens.append((self._LITERAL, source[start:index], start))
                continue
            if self._is_identifier_start(character):
                start = index
                index += 1
                while index < len(source) and self._is_identifier_part(source[index]):
                    index += 1
                value = source[start:index]
                token_type = (
                    self._LITERAL if value in {"true", "false"} else self._IDENTIFIER
                )
                tokens.append((token_type, value, start))
                continue
            raise _WhenFormatError("unsupported token", index)
        tokens.append((self._END, "", len(source)))
        return tokens

    @staticmethod
    def _is_identifier_start(character: str) -> bool:
        return character.isascii() and (character.isalpha() or character == "_")

    @classmethod
    def _is_identifier_part(cls, character: str) -> bool:
        return cls._is_identifier_start(character) or (
            character.isascii() and character.isdigit()
        ) or character == "."


ManifestV2 = PluginManifestV2


__all__ = [
    "ManifestV2",
    "ManifestValidationError",
    "PluginCommandContribution",
    "PluginConfigurationContribution",
    "PluginContributions",
    "PluginManifestErrorCode",
    "PluginManifestV2",
    "PluginManifestValidator",
    "PluginMenuContribution",
    "PluginNavigationContainerContribution",
    "PluginType",
    "PluginViewContribution",
    "build_manifest",
    "load_file",
    "load_toml",
]
