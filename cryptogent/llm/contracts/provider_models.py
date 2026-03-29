from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .context_models import LLMContextBundle
from .task_models import LLMTaskName, TaskConstraints, TaskOptions


@dataclass(frozen=True)
class ProviderRequest:
    task_name: LLMTaskName
    prompt: str
    context: LLMContextBundle
    constraints: TaskConstraints
    options: TaskOptions
    system_message: str | None = None
    user_message: str | None = None
    developer_message: str | None = None
    response_format: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.task_name, LLMTaskName):
            raise TypeError("task_name must be LLMTaskName")
        if not isinstance(self.context, LLMContextBundle):
            raise TypeError("context must be LLMContextBundle")
        if not isinstance(self.constraints, TaskConstraints):
            raise TypeError("constraints must be TaskConstraints")
        if not isinstance(self.options, TaskOptions):
            raise TypeError("options must be TaskOptions")


@dataclass(frozen=True)
class ProviderCapabilities:
    provider_name: str
    supports_streaming: bool
    supports_tools: bool
    max_context_tokens: int | None
    max_output_tokens: int | None


@dataclass(frozen=True)
class LLMRawResponse:
    provider_name: str
    model: str
    content: str
    raw_payload: dict[str, Any]
    usage: dict[str, Any] | None
    created_at_utc: str
    latency_ms: int | None = None
    finish_reason: str | None = None
