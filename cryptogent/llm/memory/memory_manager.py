from __future__ import annotations

from typing import Any
from pathlib import Path

from cryptogent.llm.contracts import LLMTaskName, MemoryBundle
from cryptogent.llm.memory.filters import filter_memory
from cryptogent.llm.memory.policies import MemoryPolicy, get_policy
from cryptogent.llm.memory.storage.factory import build_repository
from cryptogent.llm.memory.storage.memory_item import MemoryItem
from cryptogent.llm.memory.storage.repository import MemoryRepository
from cryptogent.llm.memory.storage.retriever import MemoryRetriever
from cryptogent.llm.memory.storage.txt_repository import TxtMemoryRepository
from cryptogent.llm.memory.storage.in_memory_repository import InMemoryRepository
from cryptogent.config.io import load_config, ensure_default_config, ConfigPaths


class MemoryManager:
    def __init__(self, repository: MemoryRepository | None = None) -> None:
        self._repository = repository

    def retrieve_memory(
        self,
        *,
        task_name: LLMTaskName,
        memory_key: str | None = None,
        raw_inputs: dict[str, Any] | None = None,
        conversation_state: dict[str, Any] | None,
        retrieval_limit: int | None,
        policy: MemoryPolicy | None = None,
    ) -> MemoryBundle:
        policy = policy or get_policy(task_name)
        effective_limit = policy.max_items
        if retrieval_limit is not None:
            if effective_limit is None:
                effective_limit = retrieval_limit
            else:
                effective_limit = min(effective_limit, retrieval_limit)
        if effective_limit != policy.max_items:
            policy = MemoryPolicy(
                enabled=policy.enabled,
                max_items=effective_limit,
                recency_days=policy.recency_days,
                min_score=policy.min_score,
                policy_name=policy.policy_name,
            )
        if not policy.enabled:
            return MemoryBundle(items=tuple(), source=None)

        items: list[dict[str, Any]] = []
        if self._repository and memory_key:
            retriever = MemoryRetriever(self._repository)
            stored = retriever.retrieve(
                memory_key=memory_key,
                task_name=task_name.value,
                policy=policy,
            )
            for item in stored:
                items.append(item.__dict__)
        else:
            items = self._gather_items(raw_inputs=raw_inputs or {}, conversation_state=conversation_state)

        filtered = filter_memory(items, policy)
        metadata = {"count": len(filtered), "policy": policy.policy_name, "memory_key": memory_key}
        return MemoryBundle(items=tuple(filtered), source=policy.policy_name, metadata=metadata)

    def append(
        self,
        *,
        memory_key: str,
        task_name: LLMTaskName,
        role: str,
        content: str,
        timestamp_utc: str,
        source: str | None = None,
        score: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not self._repository:
            return
        item = MemoryItem(
            memory_key=memory_key,
            task_name=task_name.value,
            role=role,
            content=content,
            timestamp_utc=timestamp_utc,
            source=source,
            score=score,
            metadata=metadata,
        )
        self._repository.append(item)

    def _gather_items(
        self,
        *,
        raw_inputs: dict[str, Any],
        conversation_state: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        if conversation_state:
            conv_items = conversation_state.get("recent_memory") or conversation_state.get("items") or []
            if isinstance(conv_items, list):
                items.extend([i for i in conv_items if isinstance(i, dict)])
        raw_items = raw_inputs.get("memory_items") or raw_inputs.get("memory") or []
        if isinstance(raw_items, list):
            items.extend([i for i in raw_items if isinstance(i, dict)])
        return items


def build_default_memory_manager(*, config_path: Path | None = None) -> MemoryManager:
    paths = ConfigPaths.from_cli(config_path=config_path, db_path=None)
    config_path = ensure_default_config(paths.config_path)
    cfg = load_config(config_path)
    backend = getattr(cfg, "llm_memory_backend", "sqlite") or "sqlite"
    path = getattr(cfg, "llm_memory_path", None) or "llm_memory.sqlite3"
    repo = build_repository(backend=backend, path=Path(path))
    return MemoryManager(repository=repo)
