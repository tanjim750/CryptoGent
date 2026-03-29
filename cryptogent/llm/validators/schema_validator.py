from __future__ import annotations

from typing import Any

from cryptogent.llm.contracts import SchemaBundle


def validate_schema(
    data: dict[str, Any], schema_bundle: SchemaBundle | None
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if schema_bundle is None or not isinstance(schema_bundle.output_schema, dict):
        return errors, warnings
    schema = schema_bundle.output_schema
    required = schema.get("required")
    if isinstance(required, list):
        missing = [k for k in required if k not in data]
        if missing:
            errors.append(f"missing_required_fields:{','.join(missing)}")
    props = schema.get("properties")
    if isinstance(props, dict):
        additional = schema.get("additionalProperties")
        if additional is False:
            unknown = [k for k in data.keys() if k not in props]
            if unknown:
                errors.append(f"unknown_fields:{','.join(unknown)}")
    return errors, warnings
