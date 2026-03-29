from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from cryptogent.llm.contracts import LLMRawResponse, ProviderCapabilities, ProviderRequest
from cryptogent.llm.providers.base import BaseProvider


class OllamaProvider(BaseProvider):
    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_name="ollama",
            supports_streaming=False,
            supports_tools=False,
            max_context_tokens=None,
            max_output_tokens=None,
        )

    def generate(self, request: ProviderRequest) -> LLMRawResponse:
        self._enforce_limits(request)
        client = self._ensure_client()

        system_message = request.system_message or ""
        user_message = request.user_message or request.prompt

        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": user_message,
            "system": system_message,
            "options": {
                "temperature": request.constraints.temperature,
                "top_p": request.constraints.top_p,
                "num_predict": request.constraints.max_tokens,
            },
        }

        if self._json_mode or (request.response_format or "").lower() == "json":
            payload["format"] = "json"

        t0 = time.time()
        self._log("request", payload)
        raw = client(payload)
        self._log("response", raw)
        latency_ms = int((time.time() - t0) * 1000)
        content = _extract_content(raw)
        usage = raw.get("usage") if isinstance(raw, dict) else None
        finish_reason = _extract_finish_reason(raw)
        created_at = datetime.now(tz=timezone.utc).isoformat()

        return LLMRawResponse(
            provider_name="ollama",
            model=self.model,
            content=content,
            raw_payload=raw if isinstance(raw, dict) else {"raw": raw},
            usage=usage if isinstance(usage, dict) else None,
            latency_ms=latency_ms,
            finish_reason=finish_reason,
            created_at_utc=created_at,
        )


def _extract_content(raw: dict[str, Any]) -> str:
    if "content" in raw and isinstance(raw["content"], str):
        return raw["content"]
    if "response" in raw and isinstance(raw["response"], str):
        return raw["response"]
    return ""


def _extract_finish_reason(raw: dict[str, Any]) -> str | None:
    reason = raw.get("done_reason")
    if isinstance(reason, str):
        return reason
    return None
