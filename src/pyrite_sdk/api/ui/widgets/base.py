from ....utils.ui import _serialize_value
from ....interfaces.ui import PageType, WidgetType, EventType, ContextNodeType
from ..context_manager import ContextNode
from ..sentence import Var
from typing import Any, Optional

class Widget(ContextNode):
    def __init__(self, name: str, multi_child: bool = False, **kwargs: Any) -> None:
        self.name: str = name
        self.args: dict[str, Any] = kwargs
        self.page: Optional[PageType] = None
        super().__init__(name,
                        multi_child=multi_child,
                        **kwargs)

    def setup(self) -> None:
        assert isinstance(self.parent, (WidgetType, PageType))
        if self.parent is None or self.parent.page is None:
            raise Exception("Widget cannot find page")
        self.page = self.parent.page
        self.setup_child()
        for arg in self.args.values():
            if isinstance(arg, EventType):
                self.setup_event(arg)

    def setup_event(self, event: Optional[EventType] = None) -> None:
        if not self.page:
            raise Exception("Widget cannot find page")
        if not event:
            return
        event.events = self.page.events
        event.setup()

    def _setup_child(self, keyname: str, child: list[ContextNodeType]) -> None:
        _child = []
        for c in child:
            if not isinstance(c, WidgetType):
                continue
            _child.append(c)
            c.parent = self
            c.setup()
        if len(_child) == 1:
            _child = _child[0]
        self.args[keyname] = _child

    def setup_child(self) -> None:
        for alias_name, child in self.child_nodes.items():
            assert isinstance(child, list)
            self._setup_child(alias_name, child)
        # for arg in self.args.values():
        #     if isinstance(arg, Assets):
        #         arg.parent = self
        #         arg.page = self.page

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
