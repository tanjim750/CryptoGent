from cryptogent.llm.contracts import LLMTaskName, SchemaBundle
from cryptogent.llm.context import ContextManager
from cryptogent.llm.prompts import build_prompt


def test_prompt_builder_injects_schema() -> None:
    ctx = ContextManager().build(
        task_name=LLMTaskName.TRADE_DECISION,
        raw_inputs={"symbol": "BTCUSDT"},
    )
    schema = SchemaBundle(
        input_schema=None,
        output_schema={
            "type": "object",
            "properties": {"decision": {"type": "string"}},
            "required": ["decision"],
            "version": "v1",
        },
    )
    pkg = build_prompt(
        task_name=LLMTaskName.TRADE_DECISION,
        context_bundle=ctx,
        memory_bundle=None,
        schema_bundle=schema,
    )
    assert "schema_version" in (pkg.metadata or {})
    assert "Schema:" in (pkg.metadata or {}).get("user_message", "")
