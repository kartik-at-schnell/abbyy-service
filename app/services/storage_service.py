from pathlib import Path
from typing import Union


class StorageService:
    """Simple file storage abstraction (local filesystem)."""

    def __init__(self, base_path: Union[str, Path]):
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)

    def save(self, filename: str, data: bytes) -> str:
        path = self.base / filename
        path.write_bytes(data)
        return str(path)

