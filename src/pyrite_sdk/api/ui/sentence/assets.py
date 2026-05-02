from ....utils.ui import RFWSerializable
from ....interfaces.ui import PageType, ContextNodeType
from pathlib import Path
from typing import Optional

class Assets(RFWSerializable):
    def __init__(self, path: str | Path | None = None) -> None:
        self.parent: Optional[ContextNodeType] = None
        self.page: Optional[PageType] = None
        self.path: Path = Path(path) if path else Path()

    def to_rfw(self) -> str:
        assert isinstance(self.page, PageType)
        if isinstance(self.path, Path) and self.path != Path():
            return f'"{Path(self.page.assets_directory) / self.path}"'
        return f'"{self.page.assets_directory}"'

    def __truediv__(self, other: str) -> "Assets":
        if isinstance(self.path, Path) and self.path != Path():
            return Assets(self.path / other)
        return Assets(Path(other))