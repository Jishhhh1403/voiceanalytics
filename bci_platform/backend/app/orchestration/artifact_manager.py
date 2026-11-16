from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from ..config import Settings


class ArtifactManager:
    def __init__(self, settings: Settings, run_id: str) -> None:
        self.settings = settings
        self.run_id = run_id
        self.root = settings.artifacts_dir / run_id
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, *parts: str) -> Path:
        p = self.root.joinpath(*parts)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def write_json(self, rel: str, data: Any) -> str:
        p = self.path(rel)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return self._checksum(p)

    def write_text(self, rel: str, text: str) -> str:
        p = self.path(rel)
        p.write_text(text, encoding="utf-8")
        return self._checksum(p)

    def write_npz(self, rel: str, **arrays: Any) -> str:
        p = self.path(rel)
        np.savez_compressed(p, **arrays)
        return self._checksum(p)

    def load_json(self, rel: str) -> Any:
        return json.loads(self.path(rel).read_text(encoding="utf-8"))

    @staticmethod
    def _checksum(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
