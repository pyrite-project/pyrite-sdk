import json
import unittest

from pyrite_sdk.api.components import (
    AUTO_ID_PREFIX,
    Button,
    Column,
    ListItem,
    Text,
    TextField,
    VirtualList,
)
from pyrite_sdk.api.view import (
    MAX_VIEW_PAYLOAD_BYTES,
    ViewModel,
    ViewProtocolError,
)
from pyrite_sdk.core.errors import SdkApiError


class FakeBridge:
    def __init__(self, deliver=True):
        self.calls = []
        self.deliver = deliver

    def push_wait_response(self, envelope, callback=None, client=None):
        self.calls.append((envelope, callback, client))
        return self.deliver

    def types(self):
        return [envelope.type for envelope, _, _ in self.calls]

    def last(self):
        envelope, callback, _ = self.calls[-1]
        return envelope, callback

    def patches(self):
        return [e for e, _, _ in self.calls if e.type == "sdk.view.patch"]


def tree(label, handler=None):
    return Column(
        Text(label),
        Button(id="go", label="Go", on_press=handler or (lambda payload: None)),
        id="root",
    )


def value_of(model):
    """Returns the first Text/Button label in the (single) root component."""
    root = model.nodes[0]["component"]
    return root["children"][0]["props"]["value"]


def text_field_id(node):
    return node["children"][0]["props"]["id"]


class ComponentRootShapeTest(unittest.TestCase):
    def setUp(self):
        self.bridge = FakeBridge()
        self.model = ViewModel(self.bridge, "panel", instance_id="i1")

    def test_bare_component_root_is_wrapped_with_addressable_id(self):
        self.model.snapshot([tree("one")])

        node = self.bridge.last()[0].payload["nodes"][0]
        self.assertEqual(set(node), {"id", "component"})
        self.assertEqual(node["id"], "root")
        self.assertEqual(node["component"]["props"]["id"], "root")

    def test_component_root_without_id_gets_a_stable_structural_id(self):
        self.model.snapshot([Column(Text("one"))])
        first = self.bridge.last()[0].payload["nodes"][0]["id"]
        self.assertTrue(first.startswith(AUTO_ID_PREFIX))

        # A rebuilt tree is a different object graph but the same structure.
        self.model.snapshot([Column(Text("one"))])
        second = self.bridge.last()[0].payload["nodes"][0]["id"]
        self.assertEqual(first, second)

    def test_nested_stateful_component_without_id_keeps_stable_id(self):
        self.model.snapshot([Column(TextField(value="a"), id="root")])
        first = self.bridge.last()[0].payload["nodes"][0]["component"]
        first_id = text_field_id(first)
        self.assertTrue(first_id.startswith(AUTO_ID_PREFIX))

        self.model.snapshot([Column(TextField(value="a"), id="root")])
        second = self.bridge.last()[0].payload["nodes"][0]["component"]
        self.assertEqual(text_field_id(second), first_id)

    def test_explicit_id_anchors_descendant_ids_across_sibling_edits(self):
        def build(extra=False):
            children = [Text("before")]
            if extra:
                children.append(Text("inserted"))
            children.append(Column(TextField(value="v"), id="editor"))
            return Column(*children, id="root")

        self.model.snapshot([build()])
        first = self.bridge.last()[0].payload["nodes"][0]["component"]
        first_field_id = first["children"][1]["children"][0]["props"]["id"]
        self.assertTrue(first_field_id.startswith(AUTO_ID_PREFIX))

        # Inserting a sibling before the explicitly addressed subtree must not
        # shift the auto ids of its descendants.
        self.model.snapshot([build(extra=True)])
        second = self.bridge.last()[0].payload["nodes"][0]["component"]
        editor = second["children"][2]
        self.assertEqual(editor["props"]["id"], "editor")
        self.assertEqual(editor["children"][0]["props"]["id"], first_field_id)

    def test_data_item_auto_ids_are_stable_across_rebuilds(self):
        def build():
            return Column(
                VirtualList(items=[ListItem(label="row")], id="list"),
                id="root",
            )

        self.model.snapshot([build()])
        first = self.bridge.last()[0].payload["nodes"][0]["component"]
        first_item = first["children"][0]["props"]["items"][0]["id"]

        self.model.snapshot([build()])
        second = self.bridge.last()[0].payload["nodes"][0]["component"]
        self.assertEqual(second["children"][0]["props"]["items"][0]["id"],
                         first_item)

    def test_component_view_rejects_mixed_roots(self):
        with self.assertRaisesRegex(ViewProtocolError, "exactly one root"):
            self.model.snapshot([Column(Text("a")), {"id": "data"}])
        self.assertEqual(self.model.nodes, [])

    def test_snapshot_payload_failure_leaves_model_unchanged(self):
        self.model.snapshot([{"id": "ok"}])
        before = (self.model.nodes, self.model.revision)

        oversized = "x" * (MAX_VIEW_PAYLOAD_BYTES + 64)
        with self.assertRaisesRegex(ViewProtocolError, "bytes"):
            self.model.snapshot([{"id": "big", "value": oversized}])

        self.assertEqual(self.model.nodes, before[0])
        self.assertEqual(self.model.revision, before[1])


class ComponentRootHelperTest(unittest.TestCase):
    def test_set_content_wraps_and_update_root_patches_by_wrapper_id(self):
        bridge = FakeBridge()
        model = ViewModel(bridge, "panel", instance_id="i1")

        model.set_content(tree("one"))
        self.assertEqual(model.component_root_id, "root")
        self.assertEqual(
            bridge.last()[0].payload["nodes"][0]["id"], "root"
        )

        bridge.calls.clear()
        model.update_root(tree("two"))
        op = bridge.last()[0].payload["ops"][0]
        self.assertEqual(op["id"], "root")
        self.assertEqual(value_of(model), "two")

    def test_update_root_requires_a_component_view(self):
        bridge = FakeBridge()
        model = ViewModel(bridge, "outline", instance_id="i1")
        model.snapshot([{"id": "a"}])
        with self.assertRaisesRegex(ViewProtocolError, "no component root"):
            model.update_root(tree("one"))


class ComponentPatchTest(unittest.TestCase):
    def setUp(self):
        self.bridge = FakeBridge()
        self.model = ViewModel(self.bridge, "panel", instance_id="i1")
        self.model.snapshot([tree("one")])
        self.bridge.calls.clear()

    def test_update_root_component_updates_mirror_and_wire_shape(self):
        self.model.update("root", tree("two"))

        patch, _ = self.bridge.last()
        self.assertEqual(patch.type, "sdk.view.patch")
        op = patch.payload["ops"][0]
        self.assertEqual(op["op"], "update")
        self.assertEqual(op["id"], "root")
        self.assertEqual(op["data"]["component"]["props"]["id"], "root")
        self.assertEqual(value_of(self.model), "two")

    def test_update_by_wrapped_component_id_addresses_the_wrapper(self):
        model = ViewModel(self.bridge, "wrapped", instance_id="i2")
        model.snapshot(
            [{"id": "root", "component": TextField(id="search", value="a")}]
        )
        self.bridge.calls.clear()

        model.update("search", TextField(id="search", value="b"))

        op = self.bridge.last()[0].payload["ops"][0]
        self.assertEqual(op["id"], "root")
        self.assertEqual(
            model.nodes[0]["component"]["props"]["value"], "b"
        )

    def test_partial_props_update_preserves_identity_and_children(self):
        self.model.update("root", {"props": {"gap": 8}})

        node = self.model.nodes[0]
        self.assertEqual(node["id"], "root")
        self.assertEqual(node["component"]["props"]["id"], "root")
        self.assertEqual(node["component"]["props"]["gap"], 8)
        self.assertEqual(len(node["component"]["children"]), 2)

    def test_update_of_missing_id_raises_before_sending(self):
        with self.assertRaisesRegex(ViewProtocolError, "missing id ghost"):
            self.model.update("ghost", {"props": {}})
        self.assertEqual(self.bridge.patches(), [])
        self.assertFalse(self.model.has_in_flight)

    def test_update_renaming_a_component_rejects_later_ops_in_the_batch(self):
        self.model.snapshot(
            [
                {
                    "id": "wrapper",
                    "component": {
                        "type": "Column",
                        "props": {"id": "inner"},
                        "children": [
                            {
                                "type": "Text",
                                "props": {"id": "t", "value": "one"},
                            }
                        ],
                    },
                }
            ]
        )
        self.bridge.calls.clear()

        with self.assertRaisesRegex(ViewProtocolError, "missing id inner"):
            with self.model.batch():
                self.model.update(
                    "inner",
                    {
                        "type": "Text",
                        "props": {"id": "renamed", "value": "two"},
                    },
                )
                self.model.update("inner", {"props": {"value": "three"}})

        self.assertEqual(self.bridge.calls, [])
        root = self.model.nodes[0]
        self.assertEqual(root["id"], "wrapper")
        self.assertEqual(root["component"]["props"]["id"], "inner")

    def test_insert_rewrites_auto_ids_before_later_ops_in_the_batch(self):
        self.model.snapshot([{"id": "a"}])
        self.bridge.calls.clear()
        field = TextField(value="one")
        auto_id = field["props"]["id"]

        with self.assertRaisesRegex(
            ViewProtocolError, f"missing id {auto_id}"
        ):
            with self.model.batch():
                self.model.insert("field", field)
                self.model.update(auto_id, {"props": {"value": "two"}})

        self.assertEqual(self.bridge.calls, [])

    def test_move_then_inner_op_keeps_the_component_payload_in_the_shadow(self):
        self.model.snapshot(
            [
                {
                    "id": "wrapper",
                    "component": {
                        "type": "Column",
                        "props": {"id": "inner"},
                        "children": [
                            {
                                "type": "Text",
                                "props": {"id": "t", "value": "one"},
                            }
                        ],
                    },
                }
            ]
        )
        self.bridge.calls.clear()

        # The move shadow must keep the moved node itself. Replacing it with
        # its address would drop the inner component, so the follow-up op by
        # props.id would be rejected as a missing id even though pass 2 can
        # still resolve it.
        with self.model.batch():
            self.model.move("wrapper", 0)
            self.model.update("inner", {"props": {"gap": 4}})

        ops = self.bridge.last()[0].payload["ops"]
        self.assertEqual([op["op"] for op in ops], ["move", "update"])
        self.assertEqual(ops[1]["id"], "wrapper")
        self.assertEqual(
            self.model.nodes[0]["component"]["props"]["gap"], 4
        )

    def test_updated_component_is_rebound_with_new_handlers(self):
        received = []
        self.model.update("root", tree("two", received.append))

        self.assertTrue(self.model.dispatch_event("go", "press", {}))
        self.assertEqual(received, [{}])

    def test_updated_component_controller_is_rebound(self):
        self.model.update(
            "root", Column(TextField(value="after"), id="root")
        )
        field = self.model.nodes[0]["component"]["children"][0]
        field.controller.set_text("typed")
        envelope, _, _ = self.bridge.calls[-1]
        self.assertEqual(envelope.type, "sdk.view.component.invoke")
        self.assertEqual(envelope.payload["componentId"], field.id)


class ResyncRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.bridge = FakeBridge()
        self.model = ViewModel(self.bridge, "panel", instance_id="i1")
        self.model.snapshot([tree("one")])
        self.bridge.calls.clear()

    def test_rejection_applies_queued_updates_in_the_resync(self):
        self.model.update("root", tree("two"))
        self.model.update("root", tree("three"))
        self.assertEqual(self.model.pending_count, 1)

        patch_callback = self.bridge.last()[1]
        self.bridge.calls.clear()
        patch_callback(error=SdkApiError("invalidOperation", "rejected"))

        self.assertEqual(self.bridge.types(), ["sdk.view.snapshot"])
        resync = self.bridge.last()[0]
        self.assertIn("three", json.dumps(resync.payload))
        self.assertEqual(self.model.pending_count, 0)

    def test_rejection_then_nack_does_not_resync_twice(self):
        self.model.update("root", tree("two"))
        patch_callback = self.bridge.last()[1]
        self.bridge.calls.clear()

        patch_callback(error=SdkApiError("invalidOperation", "rejected"))
        self.model.nack("invalidOperation")

        self.assertEqual(self.bridge.types(), ["sdk.view.snapshot"])

    def test_nack_without_in_flight_is_ignored(self):
        self.model.nack("stale")
        self.assertEqual(self.bridge.calls, [])

    def test_stale_ack_does_not_advance_revision(self):
        self.model.update("root", tree("two"))
        self.model.ack(1)  # duplicate of the current revision
        self.assertEqual(self.model.revision, 1)
        self.assertTrue(self.model.has_in_flight)

    def test_ack_releases_the_patch_and_flushes(self):
        self.model.update("root", tree("two"))
        self.model.update("root", tree("three"))
        self.model.ack(2)
        self.assertEqual(self.model.revision, 2)
        self.assertEqual(len(self.bridge.patches()), 2)
        self.assertEqual(value_of(self.model), "three")

    def test_response_after_ack_does_not_release_the_next_patch(self):
        self.model.update("root", tree("two"))
        first_response = self.bridge.last()[1]
        self.model.update("root", tree("three"))

        # The host sends ide.view.ack before the request response. The ack
        # releases revision 2 and immediately flushes revision 3.
        self.model.ack(2)
        self.assertEqual(self.model.revision, 2)
        self.assertTrue(self.model.has_in_flight)
        self.assertEqual(self.bridge.patches()[-1].payload["revision"], 3)

        # The response for revision 2 arrives late; it must not acknowledge
        # (or release) the newly in-flight revision 3.
        first_response(data={"revision": 2})
        self.assertEqual(self.model.revision, 2)
        self.assertTrue(self.model.has_in_flight)
        self.assertEqual(len(self.bridge.patches()), 2)

        # The real response for revision 3 still releases it.
        self.bridge.last()[1](data={"revision": 3})
        self.assertFalse(self.model.has_in_flight)
        self.assertEqual(self.model.revision, 3)


class BridgeFailureTest(unittest.TestCase):
    def test_flush_keeps_pending_when_bridge_is_not_live(self):
        bridge = FakeBridge(deliver=True)
        model = ViewModel(bridge, "panel", instance_id="i1")
        model.snapshot([{"id": "a"}])
        bridge.calls.clear()
        bridge.deliver = False

        model.insert("b", {"label": "B"})

        self.assertFalse(model.has_in_flight)
        self.assertEqual(model.pending_count, 1)

        bridge.deliver = True
        self.assertTrue(model.flush())
        self.assertTrue(model.has_in_flight)
        self.assertEqual(model.pending_count, 0)
        self.assertEqual([n["id"] for n in model.nodes], ["a", "b"])

    def test_snapshot_host_error_requests_another_snapshot(self):
        bridge = FakeBridge(deliver=True)
        model = ViewModel(bridge, "panel", instance_id="i1")
        errors = []
        model.on_sync_error(errors.append)
        model.snapshot([{"id": "a"}])
        snapshot_callback = bridge.last()[1]

        snapshot_callback(error=SdkApiError("payload_too_large", "too big"))

        self.assertTrue(model.needs_snapshot)
        self.assertEqual(len(errors), 1)
        self.assertIs(model.last_sync_error, errors[0])


if __name__ == "__main__":
    unittest.main()
