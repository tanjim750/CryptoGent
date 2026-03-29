from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .task_models import LLMTaskName

@dataclass(frozen=True)
class PromptTemplate:
    name: str
    system_template: str
    user_template: str
    version: str
    description: str | None = None
    variables: tuple[str, ...] = ()


@dataclass(frozen=True)
class SchemaBundle:
    input_schema: dict[str, Any] | None
    output_schema: dict[str, Any] | None
    examples: list[dict[str, Any]] | None = None


@dataclass(frozen=True)
class PromptPackage:
    task_name: LLMTaskName
    template: PromptTemplate
    schema: SchemaBundle | None
    metadata: dict[str, Any] | None = None
