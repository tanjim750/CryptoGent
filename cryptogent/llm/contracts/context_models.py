from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .task_models import LLMTaskName, TaskConstraints, TaskOptions


@dataclass(frozen=True)
class MemoryBundle:
    items: tuple[dict[str, Any], ...]
    source: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class LLMContextBundle:
    task_name: LLMTaskName
    inputs: dict[str, Any]
    constraints: TaskConstraints
    options: TaskOptions
    memory: MemoryBundle | None
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.task_name, LLMTaskName):
            raise TypeError("task_name must be LLMTaskName")
        if not isinstance(self.constraints, TaskConstraints):
            raise TypeError("constraints must be TaskConstraints")
        if not isinstance(self.options, TaskOptions):
            raise TypeError("options must be TaskOptions")
        if self.memory is not None and not isinstance(self.memory, MemoryBundle):
            raise TypeError("memory must be MemoryBundle or None")
