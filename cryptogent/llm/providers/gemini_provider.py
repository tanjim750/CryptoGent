from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from cryptogent.llm.contracts import LLMRawResponse, ProviderCapabilities, ProviderRequest
from cryptogent.llm.providers.base import BaseProvider


class GeminiProvider(BaseProvider):
    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_name="gemini",
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
            "contents": [{"role": "user", "parts": [{"text": user_message}]}],
        }

        if system_message:
            payload["system_instruction"] = {"parts": [{"text": system_message}]}

        generation_config: dict[str, Any] = {}
        if request.constraints.temperature is not None:
            generation_config["temperature"] = request.constraints.temperature
        if request.constraints.top_p is not None:
            generation_config["topP"] = request.constraints.top_p
        if request.constraints.max_tokens is not None:
            generation_config["maxOutputTokens"] = request.constraints.max_tokens
        if generation_config:
            payload["generationConfig"] = generation_config

        # Gemini JSON mode varies by API version; rely on prompt guardrails for now.

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
            provider_name="gemini",
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
    candidates = raw.get("candidates")
    if isinstance(candidates, list) and candidates:
        c0 = candidates[0]
        if isinstance(c0, dict):
            content = c0.get("content")
            if isinstance(content, dict):
                parts = content.get("parts")
                if isinstance(parts, list) and parts:
                    text = parts[0].get("text")
                    if isinstance(text, str):
                        return text
    return ""


def _extract_finish_reason(raw: dict[str, Any]) -> str | None:
    candidates = raw.get("candidates")
    if isinstance(candidates, list) and candidates:
        c0 = candidates[0]
        if isinstance(c0, dict):
            reason = c0.get("finishReason") or c0.get("finish_reason")
            if isinstance(reason, str):
                return reason
    return None
