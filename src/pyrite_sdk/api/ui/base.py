from ...utils.ui import _serialize_value, RFWSerializable, DataSerializer
from ...interfaces.ui import PageProto, WidgetProto
from .event import Event
from .context_manager import ContextNode
from pathlib import Path
from typing import Any, Optional, TypeAlias

class Var(RFWSerializable):
    def __init__(self, *paths: str) -> None:
        self.paths: tuple[str, ...] = paths

    def __getattr__(self, key: str) -> "Var":
        return Var(*self.paths, key)

    def to_rfw(self) -> str:
        return ".".join(map(str, self.paths))

data = Var("data")
args = Var("args")
state = Var("state")

def data_(*paths: str) -> str: return f"$[{Var('data', *paths).to_rfw()}]"
def args_(*paths: str) -> str: return f"$[{Var('args', *paths).to_rfw()}]"
def state_(*paths: str) -> str: return f"$[{Var('state', *paths).to_rfw()}]"

def let(var: Var, value: Any) -> DataSerializer:
    return DataSerializer(f"set {var.to_rfw()} = {_serialize_value(value)}", serialize=False)


class Widget(ContextNode):
    def __init__(self, name: str, multi_child: bool = False, **kwargs: Any):
        self.name: str = name
        self.args: dict[str, Any] = kwargs
        self.page: Optional[PageProto] = None
        super().__init__(name,
                        multi_child=multi_child,
                        **kwargs)

    def setup(self) -> None:
        assert isinstance(self.parent, (WidgetProto, PageProto))
        if self.parent is None or self.parent.page is None:
            raise Exception("Widget cannot find page")
        self.page = self.parent.page
        self.setup_child()
        for arg in self.args.values():
            if isinstance(arg, Event):
                self.setup_event(arg)

    def setup_event(self, event: Event | None) -> None:
        if not self.page:
            raise Exception("Widget cannot find page")
        if not event:
            return
        event.events = self.page.events
        event.setup()

    def _setup_child(self, keyname: str, child: WidgetProto | list[ContextNode]) -> None:
        if isinstance(child, Widget):
            child.parent = self
            child.setup()
        else:
            for c in child:
                if not isinstance(c, Widget):
                    continue
                c.parent = self
                c.setup()
        self.args[keyname] = child

    def setup_child(self) -> None:
        print(self, self.child_nodes)
        for alias_name, child in self.child_nodes.items():
            assert isinstance(child, list)
            self._setup_child(alias_name, child)
        for arg in self.args.values():
            if isinstance(arg, Assets):
                arg.parent = self
                if self.page is not None:
                    arg.page = self.page

    def alias(self, name: str) -> "Widget":
        self.alias_name = name
        return self

    def to_rfw(self) -> str:
        args_str = ", ".join(f"{key}: {_serialize_value(value)}" for (key, value) in self.args.items() if key is not None and value is not None)
        return f"{self.name}({args_str})"

class Match(RFWSerializable):
    def __init__(self, var: Var, *cases: "Case") -> None:
        self.cases: tuple["Case", ...] = cases
        self.var: Var = var

    def to_rfw(self) -> str:
        return f"switch {self.var.to_rfw()} {{ {', '.join([a_case.to_rfw() for a_case in self.cases])} }}"

class Case(RFWSerializable):
    def __init__(self, cond: Any, value: Any) -> None:
        self.cond: Any = cond
        self.value: Any = value

    def to_rfw(self) -> str:
        return f"{_serialize_value(self.cond)}: {_serialize_value(self.value)}"

class ForLoop(RFWSerializable):
    def __init__(self, var: str, in_list: Var, *widgets: Widget) -> None:
        self.var: str = var
        self.in_list: str = in_list.to_rfw()
        self.widgets: tuple[Widget, ...] = widgets

    def to_rfw(self) -> str:
        result = f"...for {self.var} in {self.in_list}:\n"
        for widget in self.widgets:
            result += f"  {widget.to_rfw()},\n"
        return result

class Assets(RFWSerializable):
    def __init__(self, path: str | Path | None = None) -> None:
        self.parent: Optional[ContextNode] = None
        self.page: Optional[PageProto] = None
        self.path: Path = Path(path) if path else Path()

    def to_rfw(self) -> str:
        if not self.page:
            raise ValueError("Cannot find page")
        if isinstance(self.path, Path) and self.path != Path():
            return f'"{Path(self.page.assets_directory) / self.path}"'
        return f'"{self.page.assets_directory}"'

    def __truediv__(self, other: str) -> "Assets":
        if isinstance(self.path, Path) and self.path != Path():
            return Assets(self.path / other)
        return Assets(Path(other))

class VarNode(Widget):
    def __init__(self, var: Var) -> None:
        super().__init__("VarNode", var=var)
        self.var: Var = var

    def to_rfw(self) -> str:
        return self.var.to_rfw()
