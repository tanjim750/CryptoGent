from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from cryptogent.llm.contracts import LLMRawResponse, ProviderCapabilities, ProviderRequest
from cryptogent.llm.providers.base import BaseProvider


class OpenAIProvider(BaseProvider):
    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_name="openai",
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
        developer_message = request.developer_message

        messages: list[dict[str, str]] = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        if developer_message:
            messages.append({"role": "developer", "content": developer_message})
        if user_message:
            messages.append({"role": "user", "content": user_message})

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": request.constraints.temperature,
            "top_p": request.constraints.top_p,
            "max_tokens": request.constraints.max_tokens,
            "timeout_seconds": request.options.timeout_s,
        }

        if self._json_mode or (request.response_format or "").lower() == "json":
            payload["response_format"] = {"type": "json_object"}

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
            provider_name="openai",
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
    choice = None
    if "choices" in raw and isinstance(raw["choices"], list) and raw["choices"]:
        choice = raw["choices"][0]
    if isinstance(choice, dict):
        msg = choice.get("message")
        if isinstance(msg, dict) and isinstance(msg.get("content"), str):
            return msg["content"]
        if isinstance(choice.get("text"), str):
            return choice["text"]
    return ""


def _extract_finish_reason(raw: dict[str, Any]) -> str | None:
    if "choices" in raw and isinstance(raw["choices"], list) and raw["choices"]:
        choice = raw["choices"][0]
        if isinstance(choice, dict):
            reason = choice.get("finish_reason")
            if isinstance(reason, str):
                return reason
    return None
