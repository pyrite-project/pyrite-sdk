import tempfile
import unittest
from collections import UserDict
from pathlib import Path

from pyrite_sdk.models.manifest import (
    ManifestValidationError,
    PluginCommandContribution,
    PluginConfigurationContribution,
    PluginContributions,
    PluginIconReference,
    PluginManifestErrorCode,
    PluginManifestV2,
    PluginManifestValidator,
    PluginMenuContribution,
    PluginNavigationContainerContribution,
    PluginType,
    PluginViewContribution,
    build_manifest,
    load_file,
    load_toml,
)


MINIMAL_UI_TOML = """
manifest_version = 2
id = "fixture-ui"
name = "Fixture UI"
version = "1.0.0"
type = "ui"
protocol_version = 1
python_version = "3.14"
activation_events = ["onView:fixture-ui.home"]
permissions = []
platforms = ["windows", "linux", "macos", "android"]

[[contributes.navigation_containers]]
id = "fixture-ui"
title = "Fixture"
icon = { material = "extension_outlined" }

[[contributes.views]]
id = "fixture-ui.home"
container = "fixture-ui"
title = "Home"
renderer = "native.form"
"""

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "manifest_v2"


def _full_manifest() -> PluginManifestV2:
    contributions = PluginContributions(
        navigation_containers=[
            PluginNavigationContainerContribution(
                id="python-tools",
                title="Python",
                icon=PluginIconReference(material="code"),
                location="primary",
                order=100,
                when="plugin.enabled",
            )
        ],
        views=[
            PluginViewContribution(
                id="python-tools.outline",
                container="python-tools",
                title="Outline",
                renderer="native.outline",
                icon=PluginIconReference(material="account_tree_outlined"),
                order=10,
                when="runtime.language == 'python' && editor.hasDocument",
            ),
            PluginViewContribution(
                id="python-tools.variables",
                container="python-tools",
                title="Variables",
                renderer="native.variableInspector",
                order=20,
            ),
        ],
        commands=[
            PluginCommandContribution(
                id="python-tools.refreshVariables",
                title="Refresh Variables",
                icon=PluginIconReference(material="refresh"),
            )
        ],
        menus=[
            PluginMenuContribution(
                location="view/title",
                view="python-tools.variables",
                command="python-tools.refreshVariables",
                group="navigation",
                when="view.active == 'python-tools.variables'",
            )
        ],
        configuration=[
            PluginConfigurationContribution(
                id="python-tools.refreshInterval",
                title="Refresh interval",
                type="integer",
                description="Refresh interval in milliseconds",
                default=500,
                enum=[100, 500, 1000],
                order=10,
            )
        ],
    )
    return build_manifest(
        plugin_id="python-tools",
        name="Python Tools",
        version="1.0.0",
        plugin_type=PluginType.UI,
        python_version="3.14",
        author="Pyrite",
        description="Python tooling",
        activation_events=[
            "onView:python-tools.outline",
            "onView:python-tools.variables",
            "onCommand:python-tools.refreshVariables",
            "onLanguage:python",
        ],
        permissions=["editor.read", "runtime.inspect"],
        platforms=["windows", "linux", "macos", "android"],
        contributes=contributions,
    )


class ManifestV2Test(unittest.TestCase):
    def assert_error_code(self, expected: str, callback) -> None:
        with self.assertRaises(ManifestValidationError) as caught:
            callback()
        self.assertEqual(caught.exception.code, expected)

    def test_full_model_dump_round_trip(self) -> None:
        manifest = _full_manifest()

        dumped = manifest.model_dump(by_alias=True, round_trip=True)
        restored = PluginManifestV2.model_validate(dumped)
        PluginManifestValidator().validate(restored)

        self.assertEqual(restored, manifest)
        self.assertEqual(
            restored.permissions_by_resource,
            {"editor": ["read"], "runtime": ["inspect"]},
        )
        self.assertFalse(restored.auto_start)
        self.assertEqual(
            dumped["contributes"]["configuration"][0]["default"],
            500,
        )
        self.assertEqual(
            dumped["contributes"]["configuration"][0]["enum"],
            [100, 500, 1000],
        )

    def test_load_toml_and_file(self) -> None:
        manifest = load_toml(MINIMAL_UI_TOML)
        self.assertEqual(manifest.id, "fixture-ui")
        self.assertEqual(manifest.type, PluginType.UI)
        self.assertEqual(manifest.python_version, "3.14")
        self.assertEqual(manifest.contributes.views[0].renderer, "native.form")

        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "plugin.toml"
            path.write_text(MINIMAL_UI_TOML, encoding="utf-8")
            self.assertEqual(load_file(path), manifest)

    def test_shared_golden_fixtures(self) -> None:
        valid = {
            "minimal_ui": PluginType.UI,
            "full_ui": PluginType.UI,
            "data": PluginType.DATA,
            "service": PluginType.SERVICE,
        }
        for name, plugin_type in valid.items():
            with self.subTest(name=name):
                manifest = load_file(FIXTURE_ROOT / f"{name}.toml")
                self.assertEqual(manifest.manifest_version, 2)
                self.assertEqual(manifest.type, plugin_type)

        rejected = {
            "contribution_conflict": (
                PluginManifestErrorCode.CONTRIBUTION_CONFLICT
            ),
            "invalid_schema": PluginManifestErrorCode.INVALID_SCHEMA,
            "invalid_when": PluginManifestErrorCode.INVALID_WHEN,
            "integer_overflow": PluginManifestErrorCode.INVALID_SCHEMA,
            "manifest_v1": PluginManifestErrorCode.UNSUPPORTED_VERSION,
            "missing_navigation": (
                PluginManifestErrorCode.MISSING_NAVIGATION_CONTAINER
            ),
            "missing_version": PluginManifestErrorCode.MISSING_VERSION,
            "non_json_configuration": PluginManifestErrorCode.INVALID_SCHEMA,
            "rfw_renderer": PluginManifestErrorCode.RFW_RENDERER_UNSUPPORTED,
            "unknown_renderer": PluginManifestErrorCode.UNKNOWN_RENDERER,
        }
        for name, code in rejected.items():
            with self.subTest(name=name):
                self.assert_error_code(
                    code,
                    lambda name=name: load_file(FIXTURE_ROOT / f"{name}.toml"),
                )

    def test_build_helper_defaults_to_minimum_permissions(self) -> None:
        manifest = build_manifest(
            plugin_id="fixture-service",
            name="Fixture Service",
            version="1.0.0",
            plugin_type="service",
        )

        self.assertEqual(manifest.manifest_version, 2)
        self.assertEqual(manifest.protocol_version, 1)
        self.assertEqual(manifest.permissions, [])
        self.assertEqual(manifest.activation_events, [])
        self.assertEqual(manifest.contributes, PluginContributions())

    def test_build_helper_rejects_ui_without_navigation(self) -> None:
        self.assert_error_code(
            PluginManifestErrorCode.MISSING_NAVIGATION_CONTAINER,
            lambda: build_manifest(
                plugin_id="fixture-ui",
                name="Fixture UI",
                version="1.0.0",
                plugin_type="ui",
            ),
        )

    def test_parse_failures_have_stable_codes(self) -> None:
        cases = [
            ("", PluginManifestErrorCode.MISSING_VERSION),
            (
                "manifest_version = 1\n",
                PluginManifestErrorCode.UNSUPPORTED_VERSION,
            ),
            (
                "[general]\nid = 'legacy'\n",
                PluginManifestErrorCode.MISSING_VERSION,
            ),
            (
                "manifest_version = 2\nid = [\n",
                PluginManifestErrorCode.INVALID_TOML,
            ),
            (
                MINIMAL_UI_TOML + "\nunknown = true\n",
                PluginManifestErrorCode.INVALID_SCHEMA,
            ),
        ]
        for source, code in cases:
            with self.subTest(code=code):
                self.assert_error_code(code, lambda source=source: load_toml(source))

        with tempfile.TemporaryDirectory() as temp:
            self.assert_error_code(
                PluginManifestErrorCode.MISSING_MANIFEST,
                lambda: load_file(Path(temp) / "plugin.toml"),
            )

        deeply_nested = (
            'manifest_version = 2\nid = "nested"\nname = "Nested"\n'
            'version = "1.0.0"\ntype = "service"\nprotocol_version = 1\n'
            '[[contributes.configuration]]\nid = "nested.value"\n'
            'title = "Value"\ntype = "array"\ndefault = '
            + "[" * 600
            + "0"
            + "]" * 600
            + "\n"
        )
        self.assert_error_code(
            PluginManifestErrorCode.INVALID_TOML,
            lambda: load_toml(deeply_nested),
        )

    def test_renderer_icon_when_and_activation_codes(self) -> None:
        cases = [
            (
                {"renderer": "rfw", "icon": None, "when": None},
                PluginManifestErrorCode.RFW_RENDERER_UNSUPPORTED,
            ),
            (
                {"renderer": "native.unknown", "icon": None, "when": None},
                PluginManifestErrorCode.UNKNOWN_RENDERER,
            ),
            (
                {"renderer": "native.rfwatch", "icon": None, "when": None},
                PluginManifestErrorCode.UNKNOWN_RENDERER,
            ),
            (
                {
                    "renderer": "native.form",
                    "icon": PluginIconReference(material="not-an-icon"),
                    "when": None,
                },
                PluginManifestErrorCode.UNKNOWN_ICON,
            ),
            (
                {
                    "renderer": "native.form",
                    "icon": None,
                    "when": "unknown.key == true",
                },
                PluginManifestErrorCode.INVALID_WHEN,
            ),
        ]
        for overrides, code in cases:
            with self.subTest(code=code):
                manifest = self._single_view_manifest(**overrides)
                self.assert_error_code(
                    code,
                    lambda manifest=manifest: PluginManifestValidator().validate(
                        manifest
                    ),
                )

        manifest = self._single_view_manifest(renderer="native.form")
        manifest.activation_events.append("onView:fixture.missing")
        self.assert_error_code(
            PluginManifestErrorCode.INVALID_ACTIVATION_EVENT,
            lambda: PluginManifestValidator().validate(manifest),
        )

    def test_namespace_conflict_and_reference_codes(self) -> None:
        invalid_namespace = self._single_view_manifest(
            renderer="native.form",
            view_id="other.home",
        )
        self.assert_error_code(
            PluginManifestErrorCode.INVALID_CONTRIBUTION_ID,
            lambda: PluginManifestValidator().validate(invalid_namespace),
        )

        duplicate = self._single_view_manifest(renderer="native.form")
        duplicate.contributes.commands.append(
            PluginCommandContribution(id="fixture.Home", title="Conflict")
        )
        self.assert_error_code(
            PluginManifestErrorCode.CONTRIBUTION_CONFLICT,
            lambda: PluginManifestValidator().validate(duplicate),
        )

        bad_reference = self._single_view_manifest(renderer="native.form")
        bad_reference.contributes.views[0].container = "fixture.missing"
        self.assert_error_code(
            PluginManifestErrorCode.INVALID_SCHEMA,
            lambda: PluginManifestValidator().validate(bad_reference),
        )

    def test_permission_plugin_id_and_configuration_codes(self) -> None:
        invalid_id = build_manifest(
            plugin_id="fixture",
            name="Fixture",
            version="1.0.0",
            plugin_type="service",
        ).model_copy(update={"id": "bad id"})
        self.assert_error_code(
            PluginManifestErrorCode.INVALID_PLUGIN_ID,
            lambda: PluginManifestValidator().validate(invalid_id),
        )
        reserved_id = invalid_id.model_copy(update={"id": "CON"})
        self.assert_error_code(
            PluginManifestErrorCode.INVALID_PLUGIN_ID,
            lambda: PluginManifestValidator().validate(reserved_id),
        )

        invalid_permission = build_manifest(
            plugin_id="fixture",
            name="Fixture",
            version="1.0.0",
            plugin_type="service",
        ).model_copy(update={"permissions": ["file.read", "file.read"]})
        self.assert_error_code(
            PluginManifestErrorCode.INVALID_PERMISSION,
            lambda: PluginManifestValidator().validate(invalid_permission),
        )

        self.assert_error_code(
            PluginManifestErrorCode.INVALID_SCHEMA,
            lambda: build_manifest(
                plugin_id="fixture",
                name="Fixture",
                version="1.0.0",
                plugin_type="service",
                contributes=PluginContributions(
                    configuration=[
                        PluginConfigurationContribution(
                            id="fixture.count",
                            title="Count",
                            type="integer",
                            default=True,
                        )
                    ]
                ),
            ),
        )

        bom_name = MINIMAL_UI_TOML.replace(
            'name = "Fixture UI"',
            'name = "\ufeff"',
        )
        self.assertIn('name = "\ufeff"', bom_name)
        self.assert_error_code(
            PluginManifestErrorCode.INVALID_SCHEMA,
            lambda: load_toml(bom_name),
        )

    def test_configuration_types_and_enums(self) -> None:
        cases = [
            ("string", "value", ["value", "other"]),
            ("integer", 2, [1, 2]),
            ("number", 2.5, [1, 2.5]),
            ("boolean", True, [True, False]),
            ("array", ["a"], [["a"], ["b"]]),
        ]
        for configuration_type, default, enum_values in cases:
            with self.subTest(configuration_type=configuration_type):
                manifest = build_manifest(
                    plugin_id="fixture",
                    name="Fixture",
                    version="1.0.0",
                    plugin_type="service",
                    contributes=PluginContributions(
                        configuration=[
                            PluginConfigurationContribution(
                                id="fixture.setting",
                                title="Setting",
                                type=configuration_type,
                                default=default,
                                enum=enum_values,
                            )
                        ]
                    ),
                )
                self.assertEqual(
                    manifest.contributes.configuration[0].default_value,
                    default,
                )

        self.assert_error_code(
            PluginManifestErrorCode.INVALID_SCHEMA,
            lambda: build_manifest(
                plugin_id="fixture",
                name="Fixture",
                version="1.0.0",
                plugin_type="service",
                contributes=PluginContributions(
                    configuration=[
                        PluginConfigurationContribution(
                            id="fixture.setting",
                            title="Setting",
                            type="integer",
                            enum=[None],
                        )
                    ]
                ),
            ),
        )

    def test_configuration_rejects_non_json_values_and_integer_overflow(self) -> None:
        cases = [
            ("number", float("nan")),
            ("number", float("inf")),
            ("integer", 1 << 63),
            ("array", [float("nan")]),
            ("array", [UserDict({"value": 1})]),
        ]
        for configuration_type, default in cases:
            with self.subTest(configuration_type=configuration_type, default=default):
                self.assert_error_code(
                    PluginManifestErrorCode.INVALID_SCHEMA,
                    lambda configuration_type=configuration_type, default=default: build_manifest(
                        plugin_id="fixture",
                        name="Fixture",
                        version="1.0.0",
                        plugin_type="service",
                        contributes=PluginContributions(
                            configuration=[
                                PluginConfigurationContribution(
                                    id="fixture.setting",
                                    title="Setting",
                                    type=configuration_type,
                                    default=default,
                                )
                            ]
                        ),
                    ),
                )

        oversized_order = _full_manifest()
        oversized_order.contributes.views[0].order = 1 << 63
        self.assert_error_code(
            PluginManifestErrorCode.INVALID_SCHEMA,
            lambda: PluginManifestValidator().validate(oversized_order),
        )

        self.assert_error_code(
            PluginManifestErrorCode.INVALID_SCHEMA,
            lambda: build_manifest(
                plugin_id="fixture",
                name="Fixture",
                version="1.0.0",
                plugin_type="service",
                contributes=PluginContributions(
                    configuration=[
                        PluginConfigurationContribution(
                            id="fixture.setting",
                            title="Setting",
                            type="array",
                            default=[True],
                            enum=[[1]],
                        )
                    ]
                ),
            ),
        )

    def test_custom_catalogs_and_cross_plugin_conflicts(self) -> None:
        validator = PluginManifestValidator(
            supported_renderers={"native.custom"},
            supported_icons={"custom-icon"},
            context_keys={"custom.enabled"},
        )
        candidate = self._single_view_manifest(
            renderer="native.custom",
            icon=PluginIconReference(material="custom-icon"),
            when="custom.enabled == true",
        )
        validator.validate(candidate)

        installed = self._single_view_manifest(renderer="native.custom")
        installed = installed.model_copy(update={"id": "other"}, deep=True)
        installed.contributes.views[0].id = "fixture.home"
        self.assert_error_code(
            PluginManifestErrorCode.CONTRIBUTION_CONFLICT,
            lambda: validator.validate_no_conflicts(candidate, [installed]),
        )

        alias = build_manifest(
            plugin_id="Alias",
            name="Alias",
            version="1.0.0",
            plugin_type="service",
        )
        installed_alias = build_manifest(
            plugin_id="alias",
            name="alias",
            version="1.0.0",
            plugin_type="service",
        )
        self.assert_error_code(
            PluginManifestErrorCode.CONTRIBUTION_CONFLICT,
            lambda: validator.validate_no_conflicts(alias, [installed_alias]),
        )

    def test_declared_icon_assets_must_exist_below_assets(self) -> None:
        source = MINIMAL_UI_TOML.replace(
            'platforms = ["windows", "linux", "macos", "android"]',
            'platforms = ["windows", "linux", "macos", "android"]\n'
            '[icons]\n'
            'full = "assets/icon.webp"\n'
            'monochrome = "assets/icon-mono.png"',
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "plugin.toml").write_text(source, encoding="utf-8")
            (root / "assets").mkdir()
            (root / "assets" / "icon.webp").write_bytes(b"webp")
            with self.assertRaises(ManifestValidationError):
                load_file(root / "plugin.toml")
            (root / "assets" / "icon-mono.png").write_bytes(b"png")
            manifest = load_file(root / "plugin.toml")
            self.assertEqual(manifest.icons.full, "assets/icon.webp")

    def test_when_expression_grammar(self) -> None:
        valid_expressions = [
            "plugin.enabled",
            "!device.connected",
            "runtime.language == 'python'",
            "runtime.state != \"paused\" && editor.hasDocument",
            "(workspace.opened || plugin.enabled) && !view.active",
            "runtime.state == 2",
            "runtime.state == -2.5",
            "plugin.enabled == true",
            "!" * 63 + "plugin.enabled",
        ]
        for expression in valid_expressions:
            with self.subTest(expression=expression):
                PluginManifestValidator().validate(
                    self._single_view_manifest(
                        renderer="native.form",
                        when=expression,
                    )
                )

        invalid_expressions = [
            "",
            "unknown.key",
            "runtime.state === 'paused'",
            "runtime.state == null",
            "runtime.state == 2.",
            "runtime.state == 'unterminated",
            "runtime.state == 'paused' + plugin.enabled",
            "(plugin.enabled",
            "!" * 300 + "plugin.enabled",
            "!" * 64 + "plugin.enabled",
            "runtime.state == '" + "x" * 4096 + "'",
            "runtime.state == '" + "\U0001f600" * 2040 + "'",
        ]
        for expression in invalid_expressions:
            with self.subTest(expression=expression):
                manifest = self._single_view_manifest(
                    renderer="native.form",
                    when=expression,
                )
                self.assert_error_code(
                    PluginManifestErrorCode.INVALID_WHEN,
                    lambda manifest=manifest: PluginManifestValidator().validate(
                        manifest
                    ),
                )

        empty_when = MINIMAL_UI_TOML.replace(
            'renderer = "native.form"',
            'renderer = "native.form"\nwhen = ""',
        )
        self.assert_error_code(
            PluginManifestErrorCode.INVALID_WHEN,
            lambda: load_toml(empty_when),
        )
        self.assert_error_code(
            PluginManifestErrorCode.INVALID_TOML,
            lambda: load_toml(b"\xff"),
        )

    @staticmethod
    def _single_view_manifest(
        *,
        renderer: str,
        icon: PluginIconReference | None = None,
        when: str | None = None,
        view_id: str = "fixture.home",
    ) -> PluginManifestV2:
        return PluginManifestV2(
            id="fixture",
            name="Fixture",
            version="1.0.0",
            type=PluginType.UI,
            contributes=PluginContributions(
                navigation_containers=[
                    PluginNavigationContainerContribution(
                        id="fixture",
                        title="Fixture",
                    )
                ],
                views=[
                    PluginViewContribution(
                        id=view_id,
                        container="fixture",
                        title="Home",
                        renderer=renderer,
                        icon=icon,
                        when=when,
                    )
                ],
            ),
        )


if __name__ == "__main__":
    unittest.main()
