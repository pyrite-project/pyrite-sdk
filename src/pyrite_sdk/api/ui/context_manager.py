from ...utils.ui import RFWSerializable

class ContextNode(RFWSerializable):
    _stack = []
    def __init__(self, name, multi_child=False, **kwargs):
        self.name = name
        self.kwargs = kwargs
        self.parent = self.get_parent_node()
        self.child_nodes = {}
        self._child_keyname = "children" if multi_child else "child"
        self.multi_child = multi_child
        self.alias_name = None

    def __enter__(self):
        ContextNode._stack.append(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        ContextNode._stack.pop()
        if self.parent is not None and self.kwargs.get("add_to_parent", True):
            self.parent.add_child(self)

    def add_child(self, child):
        child.parent = self
        alias_name = child.alias_name if child.alias_name else self._child_keyname
        if alias_name not in self.child_nodes:
            self.child_nodes[alias_name] = []
        elif "child" in self.child_nodes and not self.multi_child:
            print(f"Too many child in {self.name}")
        self.child_nodes[alias_name].append(child)
        return child

    def remove_child(self, child):
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
    def get_parent_node(self):
        return self._stack[-1] if self._stack else None

    def __repr__(self):
        return f"{self.name}({','.join([f'{k}={v}' for k, v in self.kwargs.items()])})"

    def print_tree(self, indent=0, print_args=False):
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
    def children(self):
        if self._child_keyname in self.child_nodes and self.child_nodes[self._child_keyname]:
            return self.child_nodes[self._child_keyname]
        return []

    @property
    def child(self):
        return self.children[0] if self.children else None
