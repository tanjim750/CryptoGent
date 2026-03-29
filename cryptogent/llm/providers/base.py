from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable

from cryptogent.llm.contracts import LLMRawResponse, ProviderCapabilities, ProviderRequest


ProviderClient = Callable[[dict[str, Any]], dict[str, Any]]


class BaseProvider(ABC):
    def __init__(
        self,
        *,
        model: str,
        client: ProviderClient | None = None,
        json_mode: bool = True,
        verbose: bool = False,
        max_context_tokens: int | None = None,
        enforce_task_budget: str | None = None,
        enforce_provider_cap: str | None = None,
    ) -> None:
        self._model = model
        self._client = client
        self._json_mode = json_mode
        self._verbose = verbose
        self._max_context_tokens = max_context_tokens
        self._enforce_task_budget = enforce_task_budget
        self._enforce_provider_cap = enforce_provider_cap

    def _enforce_limits(self, request: ProviderRequest) -> None:
        from cryptogent.llm.token_policy.policies import get_policy
        from cryptogent.llm.token_policy.token_estimator import estimate_tokens

        def _mode(value: str | None) -> str:
            if not value:
                return "off"
            return value.strip().lower()

        enforce_task = _mode(self._enforce_task_budget)
        enforce_provider = _mode(self._enforce_provider_cap)

        user_text = request.user_message or request.prompt or ""
        user_tokens = estimate_tokens(user_text)
        policy = get_policy(request.task_name)
        if user_tokens > policy.max_tokens:
            msg = (
                "User tokens exceed task policy budget "
                f"({user_tokens} > {policy.max_tokens})."
            )
            if enforce_task == "block":
                raise ValueError(msg)
            if enforce_task == "warn":
                print(f"[TokenWarning] {msg}")

        if self._max_context_tokens is not None:
            system_text = request.system_message or ""
            total_tokens = estimate_tokens(system_text) + estimate_tokens(user_text)
            if total_tokens > self._max_context_tokens:
                msg = (
                    "Full prompt exceeds provider context cap "
                    f"({total_tokens} > {self._max_context_tokens})."
                )
                if enforce_provider == "block":
                    raise ValueError(msg)
                if enforce_provider == "warn":
                    print(f"[TokenWarning] {msg}")

    @property
    def model(self) -> str:
        return self._model

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        raise NotImplementedError

    @abstractmethod
    def generate(self, request: ProviderRequest) -> LLMRawResponse:
        raise NotImplementedError

    def _ensure_client(self) -> ProviderClient:
        if self._client is None:
            raise RuntimeError("Provider client not configured. Pass a client callable during initialization.")
        return self._client

    def _log(self, label: str, payload: object) -> None:
        if not self._verbose:
            return
        try:
            import json as _json

            text = _json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True)
        except Exception:
            text = str(payload)
        print(f"[{self.__class__.__name__}] {label.upper()}\n{text}\n")
