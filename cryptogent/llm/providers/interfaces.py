from __future__ import annotations

from abc import ABC, abstractmethod

from cryptogent.llm.contracts import ProviderCapabilities, ProviderRequest, LLMRawResponse


class LLMProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        raise NotImplementedError

    @abstractmethod
    def generate(self, request: ProviderRequest) -> LLMRawResponse:
        raise NotImplementedError
