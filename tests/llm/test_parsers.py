from cryptogent.llm.contracts import LLMRawResponse, LLMTaskName, SchemaBundle
from cryptogent.llm.parsers import parse_response


def _raw(content: str) -> LLMRawResponse:
    return LLMRawResponse(
        provider_name="test",
        model="test",
        content=content,
        raw_payload={},
        usage=None,
        latency_ms=None,
        finish_reason=None,
        created_at_utc="",
    )


def test_parse_strict_required_fails() -> None:
    schema = SchemaBundle(
        input_schema=None,
        output_schema={
            "type": "object",
            "properties": {"decision": {"type": "string"}},
            "required": ["decision"],
        },
    )
    parsed = parse_response(
        task_name=LLMTaskName.TRADE_DECISION,
        raw_response=_raw("{}"),
        schema_bundle=schema,
        strict_required=True,
    )
    assert parsed.structured is None
    assert any("missing_required_fields" in w for w in parsed.warnings)


def test_parse_warn_only_allows_missing() -> None:
    schema = SchemaBundle(
        input_schema=None,
        output_schema={
            "type": "object",
            "properties": {"decision": {"type": "string"}},
            "required": ["decision"],
        },
    )
    parsed = parse_response(
        task_name=LLMTaskName.TRADE_DECISION,
        raw_response=_raw("{}"),
        schema_bundle=schema,
        strict_required=False,
    )
    assert parsed.structured == {}
    assert any("missing_required_fields" in w for w in parsed.warnings)
