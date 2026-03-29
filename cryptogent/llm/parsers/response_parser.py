from __future__ import annotations

from cryptogent.llm.contracts import LLMRawResponse, LLMTaskName, ParsedLLMResult, SchemaBundle
from cryptogent.llm.parsers.error_normalizer import normalize_error
from cryptogent.llm.parsers.json_parser import parse_json
from cryptogent.llm.parsers.schema_parser import apply_schema


def parse_response(
    *,
    task_name: LLMTaskName,
    raw_response: LLMRawResponse,
    schema_bundle: SchemaBundle | None,
    strict_required: bool = True,
) -> ParsedLLMResult:
    warnings: list[str] = []
    try:
        data = parse_json(raw_response.content)
        missing = _missing_required_fields(data, schema_bundle)
        if missing and strict_required:
            raise ValueError(f"missing_required_fields: {','.join(missing)}")
        if missing and not strict_required:
            warnings.append(f"missing_required_fields: {','.join(missing)}")
        structured, coercion_errors = apply_schema(data, schema_bundle)
        if coercion_errors:
            warnings.extend([f"coercion:{err}" for err in coercion_errors])
        return ParsedLLMResult(task_name=task_name, content=raw_response.content, structured=structured, warnings=tuple(warnings))
    except Exception as exc:
        err = normalize_error(exc)
        warnings.append(f"{err.code}: {err.message}")
        return ParsedLLMResult(task_name=task_name, content=raw_response.content, structured=None, warnings=tuple(warnings))


def _missing_required_fields(data: dict[str, object], schema_bundle: SchemaBundle | None) -> list[str]:
    if schema_bundle is None or not isinstance(schema_bundle.output_schema, dict):
        return []
    required = schema_bundle.output_schema.get("required")
    if not isinstance(required, list):
        return []
    return [key for key in required if key not in data]
