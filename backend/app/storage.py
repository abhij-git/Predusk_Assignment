from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Optional

from app.config import settings


class LocalFileStorage:
    """Simple local disk storage; swap implementation for S3 etc."""

    def __init__(self, base_dir: Optional[str] = None) -> None:
        self.base = Path(base_dir or settings.upload_dir)
        self.base.mkdir(parents=True, exist_ok=True)

    def save_upload(self, filename: str, data: bytes) -> str:
        base_name = os.path.basename(filename or "unnamed").replace("\x00", "").strip() or "unnamed"
        for sep in ("/", "\\", ":"):
            base_name = base_name.replace(sep, "_")
        safe = f"{uuid.uuid4().hex}_{base_name}"
        path = self.base / safe
        path.write_bytes(data)
        return str(path.resolve())


def get_storage() -> LocalFileStorage:
    return LocalFileStorage()
