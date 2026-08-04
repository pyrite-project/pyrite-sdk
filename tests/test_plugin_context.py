import asyncio
import json
import os
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pyrite_sdk.api.path import Path as SdkPath
from pyrite_sdk.core.bridge import Bridge
from pyrite_sdk.core.context import PluginContext, PluginContextError
from pyrite_sdk.models.schema import Envelope
from pyrite_sdk.models.consts import LifecycleHook
from tests.fakes import ClientTransport, FakeClient
from tools.test_command import TestCommand


def _environment(
    root: Path,
    plugin_id: str,
    *,
    session_id: str = "session-1",
    generation: int = 1,
    capabilities=("sdk.v1",),
):
    return {
        "PYRITE_IDE_PLUGIN_ID": plugin_id,
        "PYRITE_IDE_PLUGIN_SESSION_ID": session_id,
        "PYRITE_IDE_PLUGIN_GENERATION": str(generation),
        "PYRITE_IDE_PLUGIN_DIR": str(root / "plugin"),
        "PYRITE_IDE_PLUGIN_DATA_DIR": str(root / "data"),
        "PYRITE_IDE_PLUGIN_CACHE_DIR": str(root / "cache"),
        "PYRITE_IDE_PLUGIN_TEMP_DIR": str(root / "temp"),
        "PYRITE_IDE_PLUGIN_CAPABILITIES": json.dumps(capabilities),
    }


def _handshake_context(
    root: Path,
    plugin_id: str,
    *,
    session_id: str = "session-1",
    generation: int = 1,
    capabilities=("sdk.v1",),
):
    return {
        "id": plugin_id,
        "session": session_id,
        "generation": generation,
        "pluginDir": str(root / "plugin"),
        "dataDir": str(root / "data"),
        "cacheDir": str(root / "cache"),
        "tempDir": str(root / "temp"),
        "capabilities": list(capabilities),
    }


class PluginContextTest(unittest.TestCase):
    def test_two_bridges_retain_distinct_startup_contexts(self) -> None:
        with (
            tempfile.TemporaryDirectory() as first_temp,
            tempfile.TemporaryDirectory() as second_temp,
        ):
            first_root = Path(first_temp).resolve()
            second_root = Path(second_temp).resolve()
            with patch.dict(
                os.environ,
                _environment(first_root, "first-plugin"),
                clear=True,
            ):
                first = Bridge(
                    SimpleNamespace(pages={}),
                    transport=ClientTransport(),
                )
            with patch.dict(
                os.environ,
                _environment(second_root, "second-plugin"),
                clear=True,
            ):
                second = Bridge(
                    SimpleNamespace(pages={}),
                    transport=ClientTransport(),
                )
                os.environ["PYRITE_IDE_PLUGIN_ID"] = "mutated-plugin"
                os.environ["PYRITE_IDE_PLUGIN_DIR"] = str(second_root / "mutated")

            self.assertEqual(first.context.id, "first-plugin")
            self.assertEqual(first.context.plugin_dir, first_root / "plugin")
            self.assertEqual(second.context.id, "second-plugin")
            self.assertEqual(second.context.plugin_dir, second_root / "plugin")
            self.assertEqual(SdkPath(first).plugin(), first_root / "plugin")
            self.assertEqual(SdkPath(second).plugin(), second_root / "plugin")
            with self.assertRaises(FrozenInstanceError):
                first.context.id = "changed"  # type: ignore[misc]

    def test_handshake_updates_session_context_without_changing_identity_or_paths(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            environment = _environment(
                root,
                "handshake-plugin",
                session_id="session-42",
                generation=3,
                capabilities=("startup.capability",),
            )
            with patch.dict(os.environ, environment, clear=True):
                bridge = Bridge(
                    SimpleNamespace(pages={}),
                    transport=ClientTransport(),
                )
            startup = bridge.context
            client = FakeClient(
                [
                    Envelope(
                        plugin_id="handshake-plugin",
                        session_id="session-42",
                        generation=3,
                        sequence=1,
                        type="ide.initialize",
                        payload={
                            "protocolVersion": 1,
                            "pluginId": "handshake-plugin",
                            "capabilities": ["sdk.v1", "native.views"],
                            "pluginContext": _handshake_context(
                                root,
                                "handshake-plugin",
                                session_id="session-42",
                                generation=3,
                                capabilities=("sdk.v1", "native.views"),
                            ),
                        },
                    ).model_dump_json(by_alias=True),
                    Envelope(
                        plugin_id="handshake-plugin",
                        session_id="session-42",
                        generation=3,
                        sequence=2,
                        type="ide.initialized",
                        payload={
                            "protocolVersion": 1,
                            "capabilities": ["sdk.v1"],
                        },
                    ).model_dump_json(by_alias=True),
                    Envelope(
                        plugin_id="handshake-plugin",
                        session_id="session-42",
                        generation=3,
                        sequence=3,
                        type="ide.initialize",
                        payload={
                            "protocolVersion": 1,
                            "pluginId": "handshake-plugin",
                            "capabilities": ["sdk.v1", "native.views"],
                            "pluginContext": _handshake_context(
                                root,
                                "handshake-plugin",
                                session_id="session-42",
                                generation=3,
                                capabilities=("sdk.v1", "native.views"),
                            ),
                        },
                    ).model_dump_json(by_alias=True),
                    Envelope(
                        plugin_id="other-plugin",
                        session_id="session-42",
                        generation=3,
                        sequence=4,
                        type="ide.unknown",
                        payload={},
                    ).model_dump_json(by_alias=True),
                ]
            )

            asyncio.run(bridge.handler(client))

            self.assertEqual(bridge._handshake_state, "ready")
            self.assertIsNot(bridge.context, startup)
            self.assertEqual(bridge.context.id, startup.id)
            self.assertEqual(bridge.context.plugin_dir, startup.plugin_dir)
            self.assertEqual(bridge.context.data_dir, startup.data_dir)
            self.assertEqual(bridge.context.cache_dir, startup.cache_dir)
            self.assertEqual(bridge.context.session_id, "session-42")
            self.assertEqual(bridge.context.generation, 3)
            self.assertEqual(
                bridge.context.capabilities,
                frozenset({"sdk.v1", "native.views"}),
            )
            protocol_errors = [
                Envelope.model_validate_json(raw) for raw in client.sent[2:]
            ]
            self.assertEqual(
                [envelope.type for envelope in protocol_errors],
                ["sdk.response.error", "sdk.response.error"],
            )
            self.assertIn(
                "after handshake started",
                protocol_errors[0].payload["message"],
            )
            self.assertIn(
                "mismatched plugin session",
                protocol_errors[1].payload["message"],
            )

    def test_stale_high_sequence_does_not_poison_current_session(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            bridge = Bridge(
                SimpleNamespace(pages={}, on_resume=lambda: None),
                transport=ClientTransport(),
            )
        client = FakeClient(
            [
                Envelope(
                    session_id="session-2",
                    generation=2,
                    sequence=1,
                    type="ide.initialize",
                    payload={
                        "protocolVersion": 1,
                        "pluginId": "standalone",
                        "capabilities": ["sdk.v1"],
                    },
                ).model_dump_json(by_alias=True),
                Envelope(
                    session_id="session-2",
                    generation=2,
                    sequence=2,
                    type="ide.initialized",
                    payload={
                        "protocolVersion": 1,
                        "capabilities": ["sdk.v1"],
                    },
                ).model_dump_json(by_alias=True),
                Envelope(
                    session_id="stale-session",
                    generation=1,
                    sequence=100,
                    type="ide.lifecycle.hook",
                    payload={"hook": LifecycleHook.RESUME.value},
                ).model_dump_json(by_alias=True),
                Envelope(
                    session_id="session-2",
                    generation=2,
                    sequence=3,
                    type="ide.lifecycle.hook",
                    payload={"hook": LifecycleHook.RESUME.value},
                ).model_dump_json(by_alias=True),
            ]
        )

        asyncio.run(bridge.handler(client))

        sent = [Envelope.model_validate_json(raw) for raw in client.sent]
        self.assertEqual(
            [envelope.type for envelope in sent],
            [
                "sdk.initialize",
                "sdk.ready",
                "sdk.response.error",
                "ide.response.ok",
            ],
        )
        self.assertEqual(bridge._incoming_sequence, 3)

    def test_standalone_transport_adopts_handshake_session_and_capabilities(
        self,
    ) -> None:
        with patch.dict(os.environ, {}, clear=True):
            bridge = Bridge(
                SimpleNamespace(pages={}),
                transport=ClientTransport(),
            )
        startup = bridge.context
        client = FakeClient(
            [
                Envelope(
                    session_id="handshake-session",
                    generation=7,
                    sequence=1,
                    type="ide.initialize",
                    payload={
                        "protocolVersion": 1,
                        "pluginId": "standalone",
                        "capabilities": ["sdk.v1", "native.views"],
                    },
                ).model_dump_json(by_alias=True),
                Envelope(
                    session_id="handshake-session",
                    generation=7,
                    sequence=2,
                    type="ide.initialized",
                    payload={
                        "protocolVersion": 1,
                        "capabilities": ["native.views"],
                    },
                ).model_dump_json(by_alias=True),
            ]
        )

        asyncio.run(bridge.handler(client))

        self.assertEqual(bridge.context.id, startup.id)
        self.assertEqual(bridge.context.plugin_dir, startup.plugin_dir)
        self.assertEqual(bridge.context.session_id, "handshake-session")
        self.assertEqual(bridge.context.generation, 7)
        self.assertEqual(bridge.context.capabilities, frozenset({"native.views"}))

    def test_handshake_rejects_session_that_differs_from_startup_context(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            with patch.dict(
                os.environ,
                _environment(root, "guarded-plugin", session_id="expected"),
                clear=True,
            ):
                bridge = Bridge(
                    SimpleNamespace(pages={}),
                    transport=ClientTransport(),
                )
            client = FakeClient(
                [
                    Envelope(
                        plugin_id="guarded-plugin",
                        session_id="unexpected",
                        sequence=1,
                        type="ide.initialize",
                        payload={
                            "protocolVersion": 1,
                            "pluginId": "guarded-plugin",
                            "capabilities": ["sdk.v1"],
                            "pluginContext": _handshake_context(
                                root,
                                "guarded-plugin",
                                session_id="expected",
                            ),
                        },
                    ).model_dump_json(by_alias=True)
                ]
            )

            asyncio.run(bridge.handler(client))

            response = Envelope.model_validate_json(client.sent[0])
            self.assertEqual(response.type, "sdk.response.error")
            self.assertIn("pluginContext", response.payload["message"])
            self.assertEqual(bridge.context.session_id, "expected")
            self.assertEqual(bridge._handshake_state, "pending")

    def test_managed_handshake_requires_complete_plugin_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            with patch.dict(
                os.environ,
                _environment(root, "context-required"),
                clear=True,
            ):
                bridge = Bridge(
                    SimpleNamespace(pages={}),
                    transport=ClientTransport(),
                )
            client = FakeClient(
                [
                    Envelope(
                        plugin_id="context-required",
                        session_id="session-1",
                        sequence=1,
                        type="ide.initialize",
                        payload={
                            "protocolVersion": 1,
                            "pluginId": "context-required",
                            "capabilities": ["sdk.v1"],
                        },
                    ).model_dump_json(by_alias=True)
                ]
            )

            asyncio.run(bridge.handler(client))

            response = Envelope.model_validate_json(client.sent[0])
            self.assertEqual(response.type, "sdk.response.error")
            self.assertIn("pluginContext is required", response.payload["message"])

    def test_missing_and_invalid_startup_context_are_diagnosed(self) -> None:
        with self.assertRaisesRegex(
            PluginContextError,
            "Missing plugin startup context",
        ):
            PluginContext.from_environment({})

        with self.assertRaisesRegex(
            PluginContextError,
            "Incomplete plugin startup context",
        ):
            PluginContext.from_environment({"PYRITE_IDE_PLUGIN_ID": "incomplete"})

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            relative_path = _environment(root, "relative-plugin")
            relative_path["PYRITE_IDE_PLUGIN_DIR"] = "relative/plugin"
            with self.assertRaisesRegex(
                PluginContextError,
                "must be an absolute path",
            ):
                PluginContext.from_environment(relative_path)

            invalid_capabilities = _environment(root, "invalid-capabilities")
            invalid_capabilities["PYRITE_IDE_PLUGIN_CAPABILITIES"] = "{}"
            with self.assertRaisesRegex(
                PluginContextError,
                "must be an array of strings",
            ):
                PluginContext.from_environment(invalid_capabilities)

    def test_sdk_test_loader_injects_context_without_mutating_environment(
        self,
    ) -> None:
        source = (
            Path(__file__).parent / "fixtures" / "plugins" / "minimal_native_plugin"
        ).resolve()
        command = TestCommand()

        with patch.dict(os.environ, {}, clear=True):
            command._load_module(source)
            self.assertEqual(dict(os.environ), {})

        context = command.plugin.plugin.context
        self.assertEqual(context.id, "standalone")
        self.assertEqual(context.plugin_dir, source)


if __name__ == "__main__":
    unittest.main()
