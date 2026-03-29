from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from cryptogent.llm.memory.storage.memory_item import MemoryItem
from cryptogent.llm.memory.storage.repository import MemoryRepository


class SqliteMemoryRepository(MemoryRepository):
    def __init__(self, path: Path) -> None:
        self._path = path.expanduser()
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def _ensure_schema(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_key TEXT NOT NULL,
                    task_name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp_utc TEXT NOT NULL,
                    source TEXT,
                    score REAL,
                    metadata_json TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memory_key_time ON memory_items(memory_key, timestamp_utc)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memory_task_time ON memory_items(memory_key, task_name, timestamp_utc)"
            )

    def append(self, item: MemoryItem) -> None:
        if not item.content:
            return
        meta = json.dumps(item.metadata, ensure_ascii=True, separators=(",", ":")) if item.metadata else None
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO memory_items (
                    memory_key, task_name, role, content, timestamp_utc, source, score, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.memory_key,
                    item.task_name,
                    item.role,
                    item.content,
                    item.timestamp_utc,
                    item.source,
                    item.score,
                    meta,
                ),
            )

    def fetch_recent(self, *, memory_key: str, limit: int | None, since_utc: str | None = None) -> Iterable[MemoryItem]:
        where = "memory_key = ?"
        params: list[object] = [memory_key]
        if since_utc:
            where += " AND timestamp_utc >= ?"
            params.append(since_utc)
        limit_clause = ""
        if limit is not None:
            limit_clause = "LIMIT ?"
            params.append(limit)
        query = f"""
            SELECT memory_key, task_name, role, content, timestamp_utc, source, score, metadata_json
            FROM memory_items
            WHERE {where}
            ORDER BY timestamp_utc DESC
            {limit_clause}
        """
        rows = list(self._fetch(query, params))
        rows.reverse()
        return rows

    def fetch_by_task(
        self, *, memory_key: str, task_name: str, limit: int | None, since_utc: str | None = None
    ) -> Iterable[MemoryItem]:
        where = "memory_key = ? AND task_name = ?"
        params: list[object] = [memory_key, task_name]
        if since_utc:
            where += " AND timestamp_utc >= ?"
            params.append(since_utc)
        limit_clause = ""
        if limit is not None:
            limit_clause = "LIMIT ?"
            params.append(limit)
        query = f"""
            SELECT memory_key, task_name, role, content, timestamp_utc, source, score, metadata_json
            FROM memory_items
            WHERE {where}
            ORDER BY timestamp_utc DESC
            {limit_clause}
        """
        rows = list(self._fetch(query, params))
        rows.reverse()
        return rows

    def _fetch(self, query: str, params: list[object]) -> Iterable[MemoryItem]:
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        items: list[MemoryItem] = []
        for row in rows:
            meta = None
            if row[7]:
                try:
                    meta = json.loads(row[7])
                except Exception:
                    meta = None
            items.append(
                MemoryItem(
                    memory_key=row[0],
                    task_name=row[1],
                    role=row[2],
                    content=row[3],
                    timestamp_utc=row[4],
                    source=row[5],
                    score=row[6],
                    metadata=meta,
                )
            )
        return items
