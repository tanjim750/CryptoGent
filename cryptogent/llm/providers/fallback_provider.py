from __future__ import annotations

from typing import Iterable

from cryptogent.llm.contracts import LLMRawResponse, ProviderRequest
from cryptogent.llm.providers.base import BaseProvider


class FallbackProvider(BaseProvider):
    def __init__(self, *, providers: Iterable[BaseProvider], enable_fallback: bool = False) -> None:
        self._providers = list(providers)
        self._enable_fallback = enable_fallback
        super().__init__(model="fallback", client=None, json_mode=True)

    @property
    def capabilities(self):
        if self._providers:
            return self._providers[0].capabilities
        raise RuntimeError("No providers configured for fallback.")

    def generate(self, request: ProviderRequest) -> LLMRawResponse:
        if not self._providers:
            raise RuntimeError("No providers configured for fallback.")
        if not self._enable_fallback:
            return self._providers[0].generate(request)

        last_error: Exception | None = None
        for provider in self._providers:
            try:
                return provider.generate(request)
            except Exception as exc:
                last_error = exc
        if last_error:
            raise last_error
        raise RuntimeError("Fallback provider failed without error.")
