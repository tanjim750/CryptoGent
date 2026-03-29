from __future__ import annotations

from typing import Any

from cryptogent.llm.contracts import SchemaBundle


def apply_schema(
    data: dict[str, Any],
    schema_bundle: SchemaBundle | None,
) -> tuple[dict[str, Any], list[str]]:
    if schema_bundle is None or schema_bundle.output_schema is None:
        return data, []
    schema = schema_bundle.output_schema
    if not isinstance(schema, dict):
        return data, []
    props = schema.get("properties")
    if not isinstance(props, dict):
        return data, []

    coerced: dict[str, Any] = {}
    errors: list[str] = []
    for key, spec in props.items():
        if key not in data:
            continue
        value = data.get(key)
        coerced_value, err = _coerce_value(value, spec)
        if err:
            errors.append(f"{key}:{err}")
        coerced[key] = coerced_value
    return coerced, errors


def _coerce_value(value: Any, spec: Any) -> tuple[Any, str | None]:
    if not isinstance(spec, dict):
        return value, None
    expected = spec.get("type")
    if expected == "number":
        return _to_float(value)
    if expected == "integer":
        return _to_int(value)
    if expected == "string":
        return _to_str(value)
    if expected == "array":
        return _to_list(value)
    if expected == "object":
        return (value, None) if isinstance(value, dict) else ({}, "coerce_object_failed")
    return value, None


def _to_float(value: Any) -> tuple[float | None, str | None]:
    try:
        return float(value), None
    except Exception:
        return None, "coerce_number_failed"


def _to_int(value: Any) -> tuple[int | None, str | None]:
    try:
        return int(value), None
    except Exception:
        return None, "coerce_integer_failed"


def _to_str(value: Any) -> tuple[str | None, str | None]:
    if value is None:
        return None, None
    return str(value), None


def _to_list(value: Any) -> tuple[list[Any], str | None]:
    if isinstance(value, list):
        return value, None
    if value is None:
        return [], None
    return [value], "coerce_array_wrapped"
