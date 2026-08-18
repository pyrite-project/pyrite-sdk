import unittest

from examples.debug_enhanced_plugin.device_variables import (
    OPEN_EXPANSION_TAB_ID,
    OPEN_MAIN_TAB_ID,
    PAGE_SIZE,
    VARIABLES_VIEW_ID,
    DeviceVariablesController,
)
from pyrite_sdk.api.runtime import Page, RuntimeSession, Scope, Variable
from pyrite_sdk.api.tab import ViewInstanceInfo
from pyrite_sdk.api.view import Views


class FakeBridge:
    def __init__(self):
        self.calls = []

    def push_wait_response(self, envelope, callback=None, client=None):
        self.calls.append((envelope, callback, client))


class FakeSubscription:
    def __init__(self):
        self.disposed = False

    def dispose(self):
        self.disposed = True


class FakeTabs:
    def __init__(self):
        self.calls = []

    def create_view(self, view_id, **kwargs):
        self.calls.append((view_id, kwargs))


class FakeClipboard:
    def __init__(self):
        self.set_calls = []

    def set_text(self, text):
        self.set_calls.append(text)


class FakeRuntime:
    def __init__(self):
        self.sessions_callbacks = []
        self.scopes_calls = []
        self.variables_calls = []
        self.children_calls = []
        self.handlers = {}

    def sessions(self, callback=None):
        self.sessions_callbacks.append(callback)

    def scopes(self, session_id, callback=None):
        self.scopes_calls.append((session_id, callback))

    def variables(self, session_id, scope_id, **kwargs):
        self.variables_calls.append((session_id, scope_id, kwargs))

    def children(self, reference, **kwargs):
        self.children_calls.append((reference, kwargs))

    def _subscribe(self, topic, handler, **_):
        self.handlers[topic] = handler
        return FakeSubscription()

    def on_session_created(self, handler, **kwargs):
        return self._subscribe("created", handler, **kwargs)

    def on_session_ended(self, handler, **kwargs):
        return self._subscribe("ended", handler, **kwargs)

    def on_session_state_changed(self, handler, **kwargs):
        return self._subscribe("state", handler, **kwargs)

    def on_program_paused(self, handler, **kwargs):
        return self._subscribe("paused", handler, **kwargs)

    def on_program_finished(self, handler, **kwargs):
        return self._subscribe("finished", handler, **kwargs)

    def on_backend_restarted(self, handler, **kwargs):
        return self._subscribe("restarted", handler, **kwargs)

    def on_variables_changed(self, handler, **kwargs):
        return self._subscribe("variables", handler, **kwargs)


class DeviceVariablesControllerTest(unittest.TestCase):
    def setUp(self):
        self.bridge = FakeBridge()
        self.views = Views(self.bridge)
        self.view = self.views.variable_inspector(
            VARIABLES_VIEW_ID,
            instance_id="container:debug-enhanced",
            title="设备变量",
        )
        self.model = self.view.model
        self.runtime = FakeRuntime()
        self.tabs = FakeTabs()
        self.controller = DeviceVariablesController(
            self.runtime,
            self.view,
            tabs=self.tabs,
            views=self.views,
        )
        self.controller.start()

    def complete_session(self, **changes):
        values = {
            "session_id": "device",
            "generation": 1,
            "capability": "available",
            "program_state": "idle",
        }
        values.update(changes)
        self.runtime.sessions_callbacks[-1](sessions=[RuntimeSession(**values)])

    def complete_scope(self):
        self.runtime.scopes_calls[-1][1](scopes=[Scope("globals", "globals")])

    def content(self):
        action_ids = {
            OPEN_MAIN_TAB_ID,
            OPEN_EXPANSION_TAB_ID,
        }
        return [
            node
            for node in self.controller._rendered_nodes
            if node["id"] not in action_ids
        ]

    def test_no_device_and_running_device_have_explicit_safe_placeholders(self):
        self.runtime.sessions_callbacks[-1](sessions=[])
        self.assertEqual(self.content()[0]["state"], "disconnected")

        self.controller.refresh()
        self.complete_session(program_state="running")
        self.assertEqual(self.content()[0]["state"], "running")
        self.assertEqual(self.runtime.scopes_calls, [])

    def test_unavailable_backend_never_attempts_scope_query(self):
        self.complete_session(capability="unavailable")
        self.assertEqual(self.content()[0]["state"], "unavailable")
        self.assertEqual(self.runtime.scopes_calls, [])

    def test_loads_scopes_variables_and_pages_large_collections(self):
        self.complete_session()
        self.complete_scope()
        _, _, request = self.runtime.variables_calls[-1]
        self.assertEqual(request["count"], PAGE_SIZE)
        request["callback"](
            page=Page(
                items=[
                    Variable("count", "int", "42"),
                    Variable(
                        "items",
                        "list",
                        "[1, 2]",
                        reference="device:1:items",
                        has_children=True,
                    ),
                ],
                total=120,
                start=0,
            )
        )

        by_name = {node["name"]: node for node in self.content()}
        self.assertIn("全局变量", by_name)
        self.assertEqual(by_name["count"]["icon"], "material:tag")
        self.assertEqual(by_name["items"]["childrenState"], "unloaded")
        self.assertIn("加载更多...", by_name)

    def test_expansion_requests_children_by_reference(self):
        self.complete_session()
        self.complete_scope()
        self.runtime.variables_calls[-1][2]["callback"](
            page=Page(
                items=[
                    Variable(
                        "items",
                        "list",
                        "[1]",
                        reference="device:1:items",
                        has_children=True,
                    )
                ],
                total=1,
            )
        )
        item = next(node for node in self.content() if node["name"] == "items")
        self.model.dispatch_event(
            VARIABLES_VIEW_ID,
            "requestChildren",
            {"nodeId": item["id"]},
        )
        self.assertEqual(self.runtime.children_calls[-1][0], "device:1:items")
        self.runtime.children_calls[-1][1]["callback"](
            page=Page(items=[Variable("0", "int", "1")], total=1)
        )
        child = next(node for node in self.content() if node["name"] == "0")
        self.assertEqual(child["parentId"], item["id"])

    def test_backend_restart_invalidates_references_and_drops_late_page(self):
        self.complete_session()
        self.complete_scope()
        variable_callback = self.runtime.variables_calls[-1][2]["callback"]
        self.runtime.handlers["restarted"]({"sessionId": "device", "generation": 2})
        self.assertEqual(self.controller._references, {})
        variable_callback(
            page=Page(
                items=[
                    Variable(
                        "stale",
                        "list",
                        "[]",
                        reference="device:1:stale",
                        has_children=True,
                    )
                ]
            )
        )
        self.assertNotIn("stale", [node.get("name") for node in self.content()])

    def test_refresh_command_queries_sessions_again(self):
        before = len(self.runtime.sessions_callbacks)
        self.controller.refresh()
        self.assertEqual(len(self.runtime.sessions_callbacks), before + 1)

    def test_runtime_event_refresh_is_silent_and_keeps_list(self):
        self.complete_session()
        self.complete_scope()
        self.runtime.variables_calls[-1][2]["callback"](
            page=Page(items=[Variable("count", "int", "42")], total=1)
        )
        before = len(self.runtime.sessions_callbacks)
        self.runtime.handlers["variables"]({"sessionId": "device"})
        self.assertEqual(len(self.runtime.sessions_callbacks), before + 1)
        names = [node.get("name") for node in self.content()]
        self.assertIn("count", names)
        self.assertNotIn("loading", [node.get("state") for node in self.content()])

    def test_session_ended_clears_to_disconnected_placeholder(self):
        self.complete_session()
        self.complete_scope()
        self.runtime.variables_calls[-1][2]["callback"](
            page=Page(items=[Variable("count", "int", "42")], total=1)
        )
        self.runtime.handlers["ended"]({"sessionId": "device"})
        self.assertEqual(self.content()[0]["state"], "disconnected")
        self.assertEqual(self.controller._references, {})
        self.assertIsNone(self.controller.session_id)
        self.assertIsNone(self.controller.generation)

    def test_generation_change_clears_and_shows_loading(self):
        self.complete_session()
        self.complete_scope()
        self.runtime.variables_calls[-1][2]["callback"](
            page=Page(items=[Variable("count", "int", "42")], total=1)
        )
        self.runtime.handlers["restarted"]({"sessionId": "device", "generation": 2})
        self.assertEqual(self.controller._references, {})
        self.assertEqual(self.content()[0]["state"], "loading")

    def test_tab_actions_are_rendered_in_app_bar(self):
        actions = self.controller._actions()
        self.assertEqual(
            [action.id for action in actions],
            [OPEN_MAIN_TAB_ID, OPEN_EXPANSION_TAB_ID],
        )
        self.assertEqual(actions[0].label, "在主编辑区打开设备变量")
        self.assertEqual(actions[1].label, "在拓展区打开设备变量")

    def test_context_menu_copies_variable_value(self):
        self.complete_session()
        self.complete_scope()
        self.runtime.variables_calls[-1][2]["callback"](
            page=Page(items=[Variable("count", "int", "42")], total=1)
        )
        clipboard = FakeClipboard()
        self.controller.clipboard = clipboard
        node = next(
            node for node in self.view.items if node.get("name") == "count"
        )
        menu = self.controller._context_menu(node)
        self.assertEqual(
            [item["id"] for item in menu["props"]["items"]],
            ["copy"],
        )
        menu["events"]["select"]({"itemId": "copy"})
        self.assertEqual(clipboard.set_calls, ["42"])

    def test_context_menu_omits_copy_for_scope(self):
        self.complete_session()
        self.complete_scope()
        self.runtime.variables_calls[-1][2]["callback"](
            page=Page(items=[Variable("count", "int", "42")], total=1)
        )
        scope_node = next(
            node for node in self.view.items if node.get("type") == "scope"
        )
        menu = self.controller._context_menu(scope_node)
        self.assertEqual([item["id"] for item in menu["props"]["items"]], [])

    def test_actions_create_main_and_expansion_tabs_with_current_snapshot(self):
        self.complete_session()
        self.complete_scope()
        self.runtime.variables_calls[-1][2]["callback"](
            page=Page(items=[Variable("count", "int", "42")], total=1)
        )

        for action_id, expansion, instance_id in (
            (OPEN_MAIN_TAB_ID, False, "tab:variables-main"),
            (OPEN_EXPANSION_TAB_ID, True, "tab:variables-expansion"),
        ):
            self.model.dispatch_event(
                VARIABLES_VIEW_ID,
                "select",
                {"nodeId": action_id},
            )
            view_id, kwargs = self.tabs.calls[-1]
            self.assertEqual(view_id, VARIABLES_VIEW_ID)
            self.assertEqual(kwargs["title"], "设备变量")
            self.assertEqual(kwargs["expansion"], expansion)
            kwargs["callback"](
                instance=ViewInstanceInfo(
                    "debug-enhanced",
                    "session",
                    VARIABLES_VIEW_ID,
                    instance_id,
                )
            )
            tab_model = self.views.get(instance_id, VARIABLES_VIEW_ID)
            self.assertIsNotNone(tab_model)
            self.assertIn("count", [node.get("name") for node in tab_model.nodes])


if __name__ == "__main__":
    unittest.main()
