from __future__ import annotations

from abc import ABC, abstractmethod

from cryptogent.llm.contracts import LLMTaskResult, ProviderRequest


class LLMOrchestrator(ABC):
    @abstractmethod
    def run(self, request: ProviderRequest) -> LLMTaskResult:
        raise NotImplementedError
