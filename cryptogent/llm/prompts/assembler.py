from __future__ import annotations

import json
import string

from cryptogent.llm.contracts import LLMContextBundle, MemoryBundle, PromptTemplate, TaskConstraints


def assemble_messages(
    *,
    template: PromptTemplate,
    context: LLMContextBundle,
    memory: MemoryBundle | None,
    guardrails: str,
    schema_text: str,
    fewshot_text: str | None = None,
    constraints: TaskConstraints | None = None,
) -> tuple[str, str]:
    context_json = json.dumps(context.inputs, ensure_ascii=True, separators=(",", ":"))
    memory_json = json.dumps(list(memory.items) if memory else [], ensure_ascii=True, separators=(",", ":"))
    constraints_json = json.dumps(_constraints_to_dict(constraints), ensure_ascii=True, separators=(",", ":"))

    system_parts = [template.system_template, guardrails, schema_text]
    if fewshot_text:
        system_parts.append(fewshot_text)
    system_message = "\n\n".join(p for p in system_parts if p)

    _validate_placeholders(
        template.user_template,
        required_placeholders={"task_name", "context_json", "memory_json", "constraints_json", "schema_text"},
    )
    user_message = template.user_template.format(
        task_name=context.task_name.value,
        context_json=context_json,
        memory_json=memory_json,
        constraints_json=constraints_json,
        schema_text=schema_text,
    )

    return system_message, user_message


def _constraints_to_dict(constraints: TaskConstraints | None) -> dict[str, object]:
    if constraints is None:
        return {}
    return {
        "max_tokens": constraints.max_tokens,
        "temperature": constraints.temperature,
        "top_p": constraints.top_p,
        "stop": list(constraints.stop) if constraints.stop else [],
        "response_format": constraints.response_format,
    }


def _validate_placeholders(template_text: str, *, required_placeholders: set[str]) -> None:
    formatter = string.Formatter()
    found = {field_name for _, field_name, _, _ in formatter.parse(template_text) if field_name}
    missing = required_placeholders - found
    if missing:
        raise ValueError(f"Template missing placeholders: {sorted(missing)}")
