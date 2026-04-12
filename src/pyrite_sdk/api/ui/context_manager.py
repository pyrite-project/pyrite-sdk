from ...utils.ui import RFWSerializable

class ContextNode(RFWSerializable):
    _stack = []
    def __init__(self, name,  **kwargs):
        self.name = name
        self.kwargs = kwargs
        self.parent = None
        self.children = []
        self.child = None
        self.mul_children = kwargs.get("mul_children", False)

        current_parent = ContextNode.current()
        if current_parent is not None and kwargs.get("add_to_parent", True):
            current_parent.add_child(self)

    def __enter__(self):
        ContextNode._stack.append(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        ContextNode._stack.pop()

    def add_child(self, child):
        child.parent = self
        if self.mul_children:
            self.children.append(child)
        elif self.child:
            print(f"Too many child in {self.name}")
        else:
            self.child = child
        return child

    def remove_child(self, child):
        try:
            if self.mul_children:
                self.children.remove(child)
            elif self.child is child:
                self.child = None
            else:
                print(f"Cannot find any {child} to remove")
        except ValueError:
            print(f"Cannot find any {child} to remove")
        return child

    @classmethod
    def current(self):
        return self._stack[-1] if self._stack else None

    def __repr__(self):
        return f"{self.name}({','.join([f'{k}={v}' for k, v in self.kwargs.items()])})"

    def print_tree(self, indent=0, print_args=False):
        if indent:
            print("|  " * (indent-1)+"|-" + (str(self) if print_args else f"{self.name}()"))
        else:
            print(str(self) if print_args else f"{self.name}()")
        for child in self.children:
            child.print_tree(indent + 1)
        if self.child:
            self.child.print_tree(indent + 1)
