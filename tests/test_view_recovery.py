import asyncio
import unittest

from pyrite_sdk.api.components import (
    ContextMenu,
    MenuItem,
    TreeNode,
    TreeView,
)
from pyrite_sdk.api.view import ViewModel, ViewProtocolError


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


class PatchQueueRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.bridge = FakeBridge()
        self.model = ViewModel(self.bridge, "outline", instance_id="i1")
        self.model.snapshot([{"id": "a", "label": "A"}])
        self.bridge.calls.clear()

    def test_update_of_missing_id_is_removed_before_the_next_flush(self):
        with self.assertRaisesRegex(ViewProtocolError, "missing id ghost"):
            self.model.update("ghost", {"label": "ghost"})

        self.assertEqual(self.model.pending_count, 0)
        self.assertFalse(self.model.has_in_flight)
        self.assertEqual(self.bridge.patches(), [])

        self.model.update("a", {"label": "A2"})
        patches = self.bridge.patches()
        self.assertEqual(len(patches), 1)
        self.assertEqual(patches[0].payload["ops"][0]["id"], "a")
        self.assertEqual(patches[0].payload["revision"], 2)

    def test_remove_and_move_of_missing_ids_do_not_freeze_the_queue(self):
        for method, arguments in (
            ("remove", ("ghost",)),
            ("move", ("ghost", 0)),
        ):
            with self.assertRaisesRegex(ViewProtocolError, "missing id ghost"):
                getattr(self.model, method)(*arguments)
            self.assertEqual(self.model.pending_count, 0)

        self.model.insert("b", {"label": "B"})
        patches = self.bridge.patches()
        self.assertEqual(len(patches), 1)
        self.assertEqual(patches[0].payload["ops"][0]["op"], "insert")

    def test_rejected_batch_is_dropped_without_sending_its_valid_ops(self):
        with self.assertRaisesRegex(ViewProtocolError, "missing id ghost"):
            with self.model.batch():
                self.model.update("a", {"label": "A2"})
                self.model.update("ghost", {"label": "ghost"})

        self.assertEqual(self.model.pending_count, 0)
        self.assertEqual(self.bridge.patches(), [])

        self.model.update("a", {"label": "A3"})
        self.assertEqual(len(self.bridge.patches()), 1)
        self.assertEqual(self.model.nodes[0]["label"], "A3")

    def test_bad_op_queued_during_flight_is_dropped_when_the_patch_is_acked(self):
        self.model.update("a", {"label": "A2"})
        self.assertTrue(self.model.has_in_flight)

        # The flush is deferred while a patch is in flight, so the invalid op
        # only surfaces when the ack releases the queue.
        self.model.update("ghost", {"label": "ghost"})
        self.assertEqual(self.model.pending_count, 1)

        with self.assertRaisesRegex(ViewProtocolError, "missing id ghost"):
            self.model.ack(2)

        self.assertEqual(self.model.pending_count, 0)
        self.assertIsNotNone(self.model.last_sync_error)
        self.assertIn("missing id ghost", str(self.model.last_sync_error))

        self.model.update("a", {"label": "A3"})
        patches = self.bridge.patches()
        self.assertEqual(len(patches), 2)
        self.assertEqual(patches[-1].payload["baseRevision"], 2)
        self.assertEqual(patches[-1].payload["revision"], 3)


class ContextMenuHandlerLifetimeTest(unittest.TestCase):
    def setUp(self):
        self.bridge = FakeBridge()
        self.model = ViewModel(self.bridge, "tree-view", instance_id="i1")
        self.selected = []
        self.nodes = {
            "node:run": TreeNode(id="node:run", label="run"),
            "node:stop": TreeNode(id="node:stop", label="stop"),
        }

        def provide_menu(current):
            return ContextMenu(
                id=f"menu:{current.id}",
                items=[MenuItem(id="open", label=f"Open {current.label}")],
                on_select=self.selected.append,
            )

        self.model.snapshot(
            [
                TreeView(
                    id="tree",
                    nodes=list(self.nodes.values()),
                    on_context_menu=provide_menu,
                )
            ]
        )
        self.bridge.calls.clear()

    def open_menu(self, target_id):
        return asyncio.run(
            self.model.request_context_menu(
                "tree", {"targetId": target_id}
            )
        )

    @staticmethod
    def menu_id(menu):
        return menu["props"]["id"]

    def select(self, menu, target_id):
        return self.model.dispatch_event(
            self.menu_id(menu),
            "select",
            {
                "itemId": "open",
                "targetId": target_id,
                "targetType": "treeNode",
            },
        )

    def test_menu_handlers_survive_an_unrelated_view_update(self):
        menu = self.open_menu("node:run")

        self.model.update("tree", {"props": {"selectedId": "node:run"}})
        self.assertTrue(self.model.has_in_flight)

        self.assertTrue(self.select(menu, "node:run"))
        self.assertEqual(len(self.selected), 1)
        self.assertEqual(self.selected[0].target_id, "node:run")

    def test_menu_handlers_survive_updates_while_the_view_is_hidden(self):
        menu = self.open_menu("node:run")

        self.model.visibility_sync(False)
        self.model.update("tree", {"props": {"selectedId": "node:run"}})

        self.assertTrue(self.select(menu, "node:run"))
        self.assertEqual(len(self.selected), 1)

    def test_a_new_menu_request_supersedes_the_previous_handlers(self):
        first = self.open_menu("node:run")
        second = self.open_menu("node:stop")

        self.assertFalse(self.select(first, "node:run"))
        self.assertTrue(self.select(second, "node:stop"))
        self.assertEqual(len(self.selected), 1)
        self.assertEqual(self.selected[0].target_id, "node:stop")

    def test_resync_clears_menu_handlers(self):
        menu = self.open_menu("node:run")

        self.model.resync()

        self.assertFalse(self.select(menu, "node:run"))
        self.assertEqual(self.selected, [])


if __name__ == "__main__":
    unittest.main()
