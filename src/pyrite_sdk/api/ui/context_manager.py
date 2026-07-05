from ...utils.ui import RFWSerializable
from ...interfaces.ui import ContextNodeType
from typing import Any, Optional, overload

class ContextNode(RFWSerializable):
    _stack: list[ContextNodeType] = []

    def __init__(self, name: str, multi_child: bool = False, **kwargs: Any) -> None:
        add_to_parent = kwargs.pop("add_to_parent", True)
        self.name: str = name
        self.kwargs: dict[str, Any] = kwargs
        self.parent: Optional[ContextNodeType] = self.get_parent_node()
        self.child_nodes: dict[str, list[ContextNodeType]] = {}
        self._child_keyname: str = "children" if multi_child else "child"
        self.multi_child: bool = multi_child
        self.alias_name: Optional[str] = None
        self._child_nodes: list[ContextNodeType] = []

        if self.parent is not None and add_to_parent:
            self.parent._child_nodes.append(self)

    def __enter__(self) -> ContextNodeType:
        ContextNode._stack.append(self)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        ContextNode._stack.pop()
        for _ in range(len(self._child_nodes)):
            self.add(self._child_nodes.pop(0))

    def _add(self, child: ContextNodeType) -> ContextNodeType:
        child.parent = self
        alias_name = child.alias_name if child.alias_name else self._child_keyname
        if alias_name not in self.child_nodes:
            self.child_nodes[alias_name] = []
        elif "child" in self.child_nodes and not self.multi_child:
            raise Exception(f"Too many child in {self.name}")
        self.child_nodes[alias_name].append(child)
        return child

    @overload
    def add(self, child: ContextNodeType) -> ContextNodeType: ...
    @overload
    def add(self, *children: ContextNodeType) -> list[ContextNodeType]: ...

    def add(self, child: ContextNodeType, *children: ContextNodeType) -> list[ContextNodeType] | ContextNodeType:
        if self.parent and child in self.parent._child_nodes:
            self.parent._child_nodes.remove(child)
        self._add(child)
        for c in children:
            self._add(c)
        return list(children) if children else child

    def add_to(self, parent: ContextNodeType) -> ContextNodeType:
        if self.parent and self in self.parent._child_nodes:
            self.parent._child_nodes.remove(self)
        parent.add(self)
        return self

    def remove_child(self, child: ContextNodeType) -> ContextNodeType:
        try:
            alias_name = child.alias_name if child.alias_name else self._child_keyname
            if alias_name in self.child_nodes and child in self.child_nodes[alias_name]:
                self.child_nodes[alias_name].remove(child)
            else:
                print(f"Cannot find any {child} to remove")
        except ValueError:
            print(f"Cannot find any {child} to remove")
        return child

    @classmethod
    def get_parent_node(cls) -> Optional["ContextNodeType"]:
        return cls._stack[-1] if cls._stack else None

    def __repr__(self) -> str:
        return f"{self.name}({','.join([f'{k}={v}' for k, v in self.kwargs.items()])})"

    def print_tree(self, indent: int = 0, print_args: bool = False) -> None:
        self_str = str(self) if print_args else f"{self.name}()"
        if self.alias_name:
            self_str = f"[{self.alias_name}] {self_str}"
        if indent:
            print("|  " * (indent-1)+"|-" + self_str)
        else:
            print(self_str)
        for child in self.child_nodes.values():
            for c in child:
                c.print_tree(indent + 1, print_args)

    @property
    def children(self) -> list["ContextNodeType"]:
        if self._child_keyname in self.child_nodes and self.child_nodes[self._child_keyname]:
            return self.child_nodes[self._child_keyname]
        return []

    @property
    def child(self) -> Optional["ContextNodeType"]:
        return self.children[0] if self.children else None
