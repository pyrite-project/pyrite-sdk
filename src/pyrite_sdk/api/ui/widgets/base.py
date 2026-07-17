from ....utils.ui import _serialize_value, RFWSerializable
from ....interfaces.ui import PageType, WidgetType, EventType, ContextNodeType
from ..context_manager import ContextNode
from ..sentence import Var
from typing import Any, Optional

_RFW_WIDGET_ALIASES = {
    "AnimatedAlign": "Align",
    "AnimatedContainer": "Container",
    "AnimatedPadding": "Padding",
    "AnimatedPositioned": "Positioned",
    "AnimatedPositionedDirectional": "Positioned",
}


class Widget(ContextNode):
    next_widget_id = 0
    callback_binding_names = []

    def __init__(self, name: str, multi_child: bool = False, **kwargs: Any) -> None:
        add_to_parent = kwargs.pop("add_to_parent", True)
        for value in kwargs.values():
            self._detach_arg_widgets(value)
        name = _RFW_WIDGET_ALIASES.get(name, name)
        self.widget_id: int = Widget.next_widget_id
        Widget.next_widget_id += 1
        self.name: str = name
        self.args: dict[str, Any] = kwargs
        self.page: Optional[PageType] = None
        super().__init__(name,
                        multi_child=multi_child,
                        add_to_parent=add_to_parent,
                        **kwargs)

    def register_callback_binding(self, default, bind_to="value", event="onChanged", name: Optional[str]=None):
        bind_to_value = self.args.get(bind_to)
        if not isinstance(bind_to_value, Var):
            self.args[bind_to] = name if name else Var("data", f"widget_{self.name}_{self.widget_id}")
            default = bind_to_value if bind_to_value else default
        bind_to_value = self.args.get(bind_to)
        Widget.callback_binding_names.append((self, event, bind_to_value, default))

    @staticmethod
    def _detach_arg_widgets(value: Any) -> None:
        if isinstance(value, WidgetType):
            parent = value.parent
            if parent is not None:
                while value in parent._child_nodes:
                    parent._child_nodes.remove(value)
                for children in parent.child_nodes.values():
                    while value in children:
                        children.remove(value)
            return
        if isinstance(value, dict):
            for item in value.values():
                Widget._detach_arg_widgets(item)
            return
        if isinstance(value, (list, tuple)):
            for item in value:
                Widget._detach_arg_widgets(item)

    def setup(self) -> None:
        if self.parent is None or getattr(self.parent, "page", None) is None:
            raise Exception("Widget cannot find page")
        self.page = self.parent.page
        self.setup_child()
        child_arg_keys = set(self.child_nodes)
        for key, arg in self.args.items():
            if key in child_arg_keys:
                continue
            self._setup_arg_value(arg, key)

    def setup_event(self, event: Optional[EventType] = None, event_name: Optional[str] = None) -> None:
        if not self.page:
            raise Exception("Widget cannot find page")
        if not event:
            return
        if event_name:
            event.set_default_event(self.widget_id, event_name)
        event.events = self.page.events
        event.setup()

    def _setup_arg_value(self, value: Any, event_name: Optional[str] = None) -> None:
        if isinstance(value, EventType):
            self.setup_event(value, event_name)
            return
        if isinstance(value, WidgetType):
            value.parent = self
            value.page = self.page
            value.setup()
            return
        if isinstance(value, dict):
            for key, item in value.items():
                self._setup_arg_value(item, str(key))
            return
        if isinstance(value, (list, tuple)):
            for item in value:
                self._setup_arg_value(item, event_name)
            return
        if isinstance(value, RFWSerializable):
            setup = getattr(value, "setup", None)
            if callable(setup):
                setup(self)

    def _setup_child(self, keyname: str, child: list[ContextNodeType]) -> None:
        _child = []
        for c in child:
            if not isinstance(c, WidgetType):
                continue
            _child.append(c)
            c.parent = self
            c.setup()
        if len(_child) == 1 and not self.multi_child:
            _child = _child[0]
        self.args[keyname] = _child

    def setup_child(self) -> None:
        for alias_name, child in self.child_nodes.items():
            assert isinstance(child, list)
            self._setup_child(alias_name, child)
    def alias(self, name: str) -> WidgetType:
        self.alias_name = name
        return self

    def to_rfw(self) -> str:
        args_str = ", ".join(f"{key}: {_serialize_value(value)}" for (key, value) in self.args.items() if key is not None and value is not None)
        return f"{self.name}({args_str})"

class VarWidget(Widget):
    def __init__(self, var: Var) -> None:
        super().__init__("VarNode", var=var)
        self.var: Var = var

    def to_rfw(self) -> str:
        return self.var.to_rfw()
