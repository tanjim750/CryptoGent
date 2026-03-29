from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from cryptogent.llm.audit.models import AuditRecord


class JsonlAuditRepository:
    def __init__(self, path: Path) -> None:
        self._path = path

    def append(self, record: AuditRecord) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(record.__dict__, ensure_ascii=True, separators=(",", ":"))
        with self._path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def read_all(self) -> Iterable[AuditRecord]:
        if not self._path.exists():
            return []
        records: list[AuditRecord] = []
        with self._path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    records.append(AuditRecord(**data))
                except Exception:
                    continue
        return records
