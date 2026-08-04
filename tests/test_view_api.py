import unittest

from pyrite_sdk.core.errors import SdkApiError
from pyrite_sdk.api.view import (
    MAX_PATCH_OPS,
    MAX_SNAPSHOT_NODES,
    ViewModel,
    ViewProtocolError,
    Views,
)


class FakeBridge:
    def __init__(self):
        self.calls = []

    def push_wait_response(self, envelope, callback=None, client=None):
        self.calls.append((envelope, callback, client))

    def types(self):
        return [envelope.type for envelope, _, _ in self.calls]

    def last(self):
        envelope, callback, _ = self.calls[-1]
        return envelope, callback

    def patches(self):
        return [e for e, _, _ in self.calls if e.type == "sdk.view.patch"]


class ViewModelTest(unittest.TestCase):
    def setUp(self):
        self.bridge = FakeBridge()
        self.model = ViewModel(self.bridge, "outline", instance_id="i1")
        self.model.snapshot([{"id": "a", "label": "A"}])
        self.bridge.calls.clear()

    def test_snapshot_sends_nodes_and_revision(self):
        bridge = FakeBridge()
        model = ViewModel(bridge, "outline", instance_id="i1")
        model.snapshot([{"id": "x"}])
        envelope, _ = bridge.last()
        self.assertEqual(envelope.type, "sdk.view.snapshot")
        self.assertEqual(envelope.payload["revision"], 1)
        self.assertEqual(envelope.payload["nodes"], [{"id": "x"}])
        self.assertEqual(envelope.payload["instanceId"], "i1")

    def test_single_op_sends_one_patch(self):
        self.model.insert("b", {"label": "B"})
        patches = self.bridge.patches()
        self.assertEqual(len(patches), 1)
        self.assertEqual(patches[0].payload["baseRevision"], 1)
        self.assertEqual(patches[0].payload["revision"], 2)
        self.assertEqual(patches[0].payload["ops"][0]["op"], "insert")

    def test_batch_merges_operations_into_one_patch(self):
        with self.model.batch():
            self.model.insert("b", {"label": "B"})
            self.model.update("a", {"label": "A2"})
            self.model.remove("b")
        patches = self.bridge.patches()
        self.assertEqual(len(patches), 1)
        ops = patches[0].payload["ops"]
        self.assertEqual([o["op"] for o in ops], ["insert", "update", "remove"])

    def test_at_most_one_patch_in_flight(self):
        self.model.insert("b", {"label": "B"})
        self.assertTrue(self.model.has_in_flight)
        # Further ops queue instead of sending a second patch.
        self.model.insert("c", {"label": "C"})
        self.model.insert("d", {"label": "D"})
        self.assertEqual(len(self.bridge.patches()), 1)
        self.assertEqual(self.model.pending_count, 2)

    def test_ack_releases_in_flight_and_flushes_queued_ops(self):
        self.model.insert("b", {"label": "B"})
        self.model.insert("c", {"label": "C"})
        self.model.ack(2)
        self.assertEqual(self.model.revision, 2)
        patches = self.bridge.patches()
        self.assertEqual(len(patches), 2)
        # The merged follow-up patch builds on the acked revision.
        self.assertEqual(patches[1].payload["baseRevision"], 2)
        self.assertEqual(patches[1].payload["revision"], 3)
        self.assertEqual(len(patches[1].payload["ops"]), 1)

    def test_nack_sends_a_fresh_snapshot(self):
        self.model.insert("b", {"label": "B"})
        self.bridge.calls.clear()
        self.model.nack("revisionGap")
        self.assertIn("sdk.view.snapshot", self.bridge.types())
        self.assertFalse(self.model.has_in_flight)

    def test_error_response_triggers_resync(self):
        self.model.insert("b", {"label": "B"})
        _, callback = self.bridge.last()
        self.bridge.calls.clear()
        callback(error=RuntimeError("revisionGap"))
        self.assertIn("sdk.view.snapshot", self.bridge.types())

    def test_delivery_pause_waits_for_host_resync(self):
        self.model.insert("b", {"label": "B"})
        _, callback = self.bridge.last()
        self.bridge.calls.clear()

        callback(error=SdkApiError("delivery_paused", "paused"))

        self.assertEqual(self.bridge.calls, [])
        self.assertFalse(self.model.has_in_flight)
        self.assertIn("b", [node["id"] for node in self.model.nodes])

    def test_local_mirror_tracks_applied_ops(self):
        with self.model.batch():
            self.model.insert("b", {"label": "B"})
            self.model.move("b", 0)
            self.model.update("a", {"label": "A2"})
        ids = [n["id"] for n in self.model.nodes]
        self.assertEqual(ids, ["b", "a"])
        self.assertEqual(self.model.nodes[1]["label"], "A2")

    def test_close_rejects_further_ops(self):
        self.model.close()
        with self.assertRaises(ViewProtocolError):
            self.model.insert("z", {})

    def test_snapshot_rejects_too_many_nodes(self):
        with self.assertRaisesRegex(ViewProtocolError, "nodes"):
            self.model.snapshot(
                [{"id": f"node-{index}"} for index in range(MAX_SNAPSHOT_NODES + 1)]
            )

    def test_large_patch_is_split_at_the_operation_budget(self):
        with self.model.batch():
            for index in range(MAX_PATCH_OPS + 1):
                self.model.insert(f"node-{index}", {})

        patches = self.bridge.patches()
        self.assertEqual(len(patches), 1)
        self.assertEqual(len(patches[0].payload["ops"]), MAX_PATCH_OPS)
        self.assertEqual(self.model.pending_count, 1)

    def test_hidden_view_defers_updates_until_a_fresh_snapshot(self):
        self.model.visibility_sync(False)
        self.bridge.calls.clear()

        self.model.insert("hidden", {"label": "Hidden"})

        self.assertEqual(self.bridge.calls, [])
        self.assertIn("hidden", [node["id"] for node in self.model.nodes])
        self.model.visibility_sync(True)
        self.assertEqual(self.bridge.types(), ["sdk.view.snapshot"])


class ViewRouteTest(unittest.TestCase):
    def setUp(self):
        self.bridge = FakeBridge()
        self.model = ViewModel(self.bridge, "outline", instance_id="i1")

    def test_route_starts_at_the_root(self):
        self.assertEqual(self.model.route, "home")
        self.assertEqual(self.model.route_stack, ["home"])

    def test_push_route_sends_route_and_params(self):
        self.model.push_route("detail", {"id": 7})
        envelope, _ = self.bridge.last()
        self.assertEqual(envelope.type, "sdk.view.route.push")
        self.assertEqual(envelope.payload["route"], "detail")
        self.assertEqual(envelope.payload["params"], {"id": 7})
        self.assertEqual(envelope.payload["instanceId"], "i1")

    def test_push_route_without_params_omits_them(self):
        self.model.push_route("detail")
        envelope, _ = self.bridge.last()
        self.assertNotIn("params", envelope.payload)

    def test_pop_replace_and_goto_use_their_own_commands(self):
        self.model.pop_route()
        self.model.replace_route("other")
        self.model.goto_route("root2")
        self.assertEqual(
            self.bridge.types(),
            [
                "sdk.view.route.pop",
                "sdk.view.route.replace",
                "sdk.view.route.goto",
            ],
        )

    def test_route_sync_updates_route_and_stack(self):
        self.model.route_sync("detail", ["home", "detail"], {"id": 7})
        self.assertEqual(self.model.route, "detail")
        self.assertEqual(self.model.route_stack, ["home", "detail"])
        self.assertEqual(self.model.route_params, {"id": 7})

    def test_on_route_handlers_see_each_sync(self):
        seen = []
        self.model.on_route(lambda route, params: seen.append((route, params)))
        self.model.route_sync("detail", ["home", "detail"], {"id": 1})
        self.model.route_sync("home", ["home"], {})
        self.assertEqual(seen, [("detail", {"id": 1}), ("home", {})])

    def test_routing_a_closed_view_is_rejected(self):
        self.model.close()
        with self.assertRaises(ViewProtocolError):
            self.model.push_route("detail")
        with self.assertRaises(ViewProtocolError):
            self.model.pop_route()

    def test_explicit_renderer_event_handler_survives_snapshots(self):
        received = []
        self.model.on_event("outline", "select", received.append)
        self.model.snapshot([{"id": "n1", "label": "build"}])

        self.assertTrue(
            self.model.dispatch_event("outline", "select", {"nodeId": "n1"})
        )
        self.assertEqual(received, [{"nodeId": "n1"}])

    def test_visibility_handlers_only_receive_transitions(self):
        seen = []
        self.model.on_visibility(seen.append)
        self.model.visibility_sync(True)
        self.model.visibility_sync(False)
        self.model.visibility_sync(False)
        self.model.visibility_sync(True)
        self.assertEqual(seen, [False, True])


class ViewsTest(unittest.TestCase):
    def setUp(self):
        self.bridge = FakeBridge()
        self.views = Views(self.bridge)

    def test_instances_are_independent(self):
        a = self.views.create("outline")
        b = self.views.create("outline")
        self.assertNotEqual(a.instance_id, b.instance_id)
        a.snapshot([{"id": "a"}])
        b.snapshot([{"id": "b"}])
        a.insert("a2", {})
        self.assertEqual(len(a.nodes), 2)
        self.assertEqual(len(b.nodes), 1)

    def test_handle_frame_routes_ack_to_the_right_instance(self):
        a = self.views.create("outline", instance_id="ia")
        b = self.views.create("outline", instance_id="ib")
        a.snapshot([])
        b.snapshot([])
        a.insert("x", {})
        b.insert("y", {})
        self.views.handle_frame(
            "ide.view.ack",
            {"instance": {"instanceId": "ia"}, "revision": 2},
        )
        self.assertEqual(a.revision, 2)
        self.assertFalse(a.has_in_flight)
        # b is untouched and still waiting.
        self.assertTrue(b.has_in_flight)

    def test_handle_frame_for_unknown_instance_is_ignored(self):
        self.views.handle_frame(
            "ide.view.ack", {"instance": {"instanceId": "ghost"}, "revision": 1}
        )

    def test_same_container_instance_is_isolated_by_view_id(self):
        outline = self.views.create("outline", instance_id="container:tools")
        variables = self.views.create("variables", instance_id="container:tools")
        seen = []
        outline.on_event("outline", "select", lambda payload: seen.append("outline"))
        variables.on_event(
            "variables", "select", lambda payload: seen.append("variables")
        )

        self.views.handle_frame(
            "ide.view.event",
            {
                "instance": {
                    "viewId": "outline",
                    "instanceId": "container:tools",
                },
                "componentId": "outline",
                "event": "select",
                "payload": {"nodeId": "n1"},
            },
        )

        self.assertEqual(seen, ["outline"])
        self.assertIs(self.views.get("container:tools", "outline"), outline)
        self.assertIs(self.views.get("container:tools", "variables"), variables)
        self.assertIsNone(self.views.get("container:tools"))

    def test_route_sync_reaches_only_the_addressed_instance(self):
        sidebar = self.views.create("outline", instance_id="sidebar")
        tab = self.views.create("outline", instance_id="tab")
        self.views.handle_frame(
            "ide.view.route.sync",
            {
                "instance": {"instanceId": "sidebar"},
                "route": "detail",
                "stack": ["home", "detail"],
                "params": {"id": 7},
            },
        )
        self.assertEqual(sidebar.route, "detail")
        self.assertEqual(sidebar.route_stack, ["home", "detail"])
        # Same viewId, other instance: still on its own root.
        self.assertEqual(tab.route, "home")
        self.assertEqual(tab.route_stack, ["home"])

    def test_resync_all_snapshots_every_view(self):
        a = self.views.create("outline", instance_id="ia")
        b = self.views.create("tree", instance_id="ib")
        a.snapshot([{"id": "a"}])
        b.snapshot([{"id": "b"}])
        self.bridge.calls.clear()
        self.views.resync_all()
        self.assertEqual(
            self.bridge.types(), ["sdk.view.snapshot", "sdk.view.snapshot"]
        )

    def test_visibility_frame_reaches_only_the_addressed_instance(self):
        sidebar = self.views.create("outline", instance_id="sidebar")
        tab = self.views.create("outline", instance_id="tab")
        seen = []
        sidebar.on_visibility(lambda visible: seen.append(("sidebar", visible)))
        tab.on_visibility(lambda visible: seen.append(("tab", visible)))

        self.views.handle_frame(
            "ide.view.visibility.changed",
            {"instance": {"instanceId": "sidebar"}, "visible": False},
        )

        self.assertEqual(seen, [("sidebar", False)])
        self.assertTrue(tab.visible)


if __name__ == "__main__":
    unittest.main()
