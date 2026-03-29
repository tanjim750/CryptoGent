from __future__ import annotations

from cryptogent.llm.contracts import LLMContextBundle, LLMTaskName, MemoryBundle, PromptPackage, SchemaBundle
from cryptogent.llm.prompts.assembler import assemble_messages
from cryptogent.llm.prompts.fewshot import build_fewshot
from cryptogent.llm.prompts.guardrails import build_guardrails
from cryptogent.llm.prompts.registry import get_prompt_template
from cryptogent.llm.prompts.schema_formatter import format_schema


def build_prompt(
    *,
    task_name: LLMTaskName,
    context_bundle: LLMContextBundle,
    memory_bundle: MemoryBundle | None,
    schema_bundle: SchemaBundle | None,
    prompt_version: str | None = None,
) -> PromptPackage:
    template = get_prompt_template(task_name, version=prompt_version)
    guardrails = build_guardrails(task_name)
    schema_text = format_schema(schema_bundle)
    fewshot_text = build_fewshot(schema_bundle)

    system_message, user_message = assemble_messages(
        template=template,
        context=context_bundle,
        memory=memory_bundle,
        guardrails=guardrails,
        schema_text=schema_text,
        fewshot_text=fewshot_text,
        constraints=context_bundle.constraints,
    )

    schema_version = None
    if schema_bundle and isinstance(schema_bundle.output_schema, dict):
        schema_version = schema_bundle.output_schema.get("version")

    metadata = {
        "system_message": system_message,
        "user_message": user_message,
        "developer_message": None,
        "prompt_version": template.version,
        "schema_version": schema_version,
    }

    return PromptPackage(task_name=task_name, template=template, schema=schema_bundle, metadata=metadata)
