from __future__ import annotations

from abc import ABC, abstractmethod

from .context_models import LLMContextBundle
from .prompt_models import PromptPackage
from .provider_models import LLMRawResponse, ProviderCapabilities, ProviderRequest
from .result_models import LLMTaskResult, ParsedLLMResult, ValidationDecision
from .task_models import LLMTaskName


class LLMProvider(ABC):
    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        raise NotImplementedError

    @abstractmethod
    def generate(self, request: ProviderRequest) -> LLMRawResponse:
        raise NotImplementedError


class LLMParser(ABC):
    @abstractmethod
    def parse(self, task_name: LLMTaskName, raw_response: LLMRawResponse) -> ParsedLLMResult:
        raise NotImplementedError


class LLMValidator(ABC):
    @abstractmethod
    def validate(self, parsed: ParsedLLMResult) -> ValidationDecision:
        raise NotImplementedError


class LLMOrchestrator(ABC):
    @abstractmethod
    def run_task(self, context: LLMContextBundle, prompt: PromptPackage) -> LLMTaskResult:
        raise NotImplementedError
