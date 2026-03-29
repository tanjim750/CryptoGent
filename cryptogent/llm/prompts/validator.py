from __future__ import annotations

import string
from pathlib import Path

from cryptogent.llm.contracts import LLMTaskName
from cryptogent.llm.prompts.registry import TEMPLATE_REGISTRY


REQUIRED_PLACEHOLDERS = {"task_name", "context_json", "memory_json", "constraints_json", "schema_text"}


def validate_all_templates() -> None:
    for task_name in TEMPLATE_REGISTRY:
        validate_task_template(task_name)


def validate_task_template(task_name: LLMTaskName) -> None:
    ref = TEMPLATE_REGISTRY.get(task_name)
    if ref is None:
        raise ValueError(f"No template registered for task {task_name}")
    base_dir = Path(__file__).resolve().parent
    template_path = base_dir / "templates" / ref.template_key / f"{ref.version}.txt"
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    raw = template_path.read_text(encoding="utf-8")
    system_text, user_text = _split_template(raw)
    _validate_placeholders(user_text, REQUIRED_PLACEHOLDERS, context="user")
    _validate_placeholders(system_text, set(), context="system")


def _split_template(raw: str) -> tuple[str, str]:
    system_marker = "### SYSTEM"
    user_marker = "### USER"
    if system_marker in raw and user_marker in raw:
        system_part = raw.split(system_marker, 1)[1]
        system_text, user_part = system_part.split(user_marker, 1)
        return system_text.strip(), user_part.strip()
    return "", raw.strip()


def _validate_placeholders(template_text: str, required: set[str], *, context: str) -> None:
    formatter = string.Formatter()
    found = {field_name for _, field_name, _, _ in formatter.parse(template_text) if field_name}
    missing = required - found
    if missing:
        raise ValueError(f"Template {context} missing placeholders: {sorted(missing)}")
