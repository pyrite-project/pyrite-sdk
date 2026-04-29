from typing import Protocol, runtime_checkable


@runtime_checkable
class WidgetProto(Protocol):
    ...


@runtime_checkable
class PageProto(Protocol):
    ...
