from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from cryptogent.llm.providers.base import BaseProvider
from cryptogent.llm.providers.fallback_provider import FallbackProvider
from cryptogent.llm.providers.gemini_provider import GeminiProvider
from cryptogent.llm.providers.ollama_provider import OllamaProvider
from cryptogent.llm.providers.openai_provider import OpenAIProvider


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    model: str
    client: Callable[[dict], dict]
    json_mode: bool = True
    max_context_tokens: int | None = None
    enforce_task_budget: str | None = None
    enforce_provider_cap: str | None = None


def build_provider(config: ProviderConfig) -> BaseProvider:
    name = config.name.lower().strip()
    if name == "openai":
        return OpenAIProvider(
            model=config.model,
            client=config.client,
            json_mode=config.json_mode,
            max_context_tokens=config.max_context_tokens,
            enforce_task_budget=config.enforce_task_budget,
            enforce_provider_cap=config.enforce_provider_cap,
        )
    if name == "gemini":
        return GeminiProvider(
            model=config.model,
            client=config.client,
            json_mode=config.json_mode,
            max_context_tokens=config.max_context_tokens,
            enforce_task_budget=config.enforce_task_budget,
            enforce_provider_cap=config.enforce_provider_cap,
        )
    if name == "ollama":
        return OllamaProvider(
            model=config.model,
            client=config.client,
            json_mode=config.json_mode,
            max_context_tokens=config.max_context_tokens,
            enforce_task_budget=config.enforce_task_budget,
            enforce_provider_cap=config.enforce_provider_cap,
        )
    raise ValueError(f"Unknown provider: {config.name}")


def build_fallback_provider(
    configs: list[ProviderConfig], *, enable_fallback: bool = False
) -> FallbackProvider:
    providers = [build_provider(cfg) for cfg in configs]
    return FallbackProvider(providers=providers, enable_fallback=enable_fallback)
