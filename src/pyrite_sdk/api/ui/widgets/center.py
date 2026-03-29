from .container import Container

class Center(Container):
    def __init__(self, child, padding=None):
        super().__init__(name="Center", child=child, padding=padding)