from __future__ import annotations

from cryptogent.llm.contracts import LLMTaskName


def build_guardrails(task_name: LLMTaskName) -> str:
    return (
        "Output must be valid JSON only. Do not include markdown, code fences, or extra text. "
        "Do not repeat the prompt. Do not include explanations outside the JSON."
    )
