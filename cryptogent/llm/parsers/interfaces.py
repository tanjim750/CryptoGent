from __future__ import annotations

from abc import ABC, abstractmethod

from cryptogent.llm.contracts import ParsedLLMResult, ProviderRequest, LLMRawResponse


class LLMParser(ABC):
    @abstractmethod
    def parse(self, raw: LLMRawResponse, request: ProviderRequest) -> ParsedLLMResult:
        raise NotImplementedError
