"""L3 replay fixtures. REPLAY never opens a network client."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.integrations.fortyguard.exceptions import ReplayFixtureNotFoundError


class ReplayStore:
    def __init__(self, fixture_dir: str | Path) -> None:
        self.fixture_dir = Path(fixture_dir)
        self._by_fingerprint: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self.fixture_dir.is_dir():
            return
        index_path = self.fixture_dir / "index.json"
        for path in sorted(self.fixture_dir.glob("*.json")):
            if path.name == "index.json":
                continue
            doc = json.loads(path.read_text(encoding="utf-8"))
            fingerprint = (doc.get("meta") or {}).get("fingerprint")
            if fingerprint:
                self._by_fingerprint[str(fingerprint)] = doc
        if index_path.is_file():
            index = json.loads(index_path.read_text(encoding="utf-8"))
            for fingerprint, rel in (index.get("by_fingerprint") or {}).items():
                path = self.fixture_dir / rel
                if path.is_file():
                    self._by_fingerprint[str(fingerprint)] = json.loads(
                        path.read_text(encoding="utf-8")
                    )

    def get(self, fingerprint: str) -> dict[str, Any] | None:
        return self._by_fingerprint.get(fingerprint)

    def require(self, fingerprint: str) -> dict[str, Any]:
        doc = self.get(fingerprint)
        if doc is None:
            raise ReplayFixtureNotFoundError(fingerprint)
        return doc
