from __future__ import annotations

from abc import ABC, abstractmethod

from cryptogent.llm.contracts import ParsedLLMResult, ProviderRequest, ValidationDecision


class LLMValidator(ABC):
    @abstractmethod
    def validate(self, parsed: ParsedLLMResult, request: ProviderRequest) -> ValidationDecision:
        raise NotImplementedError
