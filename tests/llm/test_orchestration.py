from cryptogent.llm.contracts import LLMTaskName, SchemaBundle
from cryptogent.llm.orchestration import OrchestrationOptions, run_llm_task
from cryptogent.llm.providers.openai_provider import OpenAIProvider


def test_orchestrator_end_to_end_success() -> None:
    def fake_client(payload: dict) -> dict:
        return {
            "choices": [
                {
                    "message": {
                        "content": (
                            "{\"decision\":\"buy\",\"confidence\":0.6,"
                            "\"rationale\":[\"trend\"],\"risk_checks\":[\"ok\"],"
                            "\"recommended_actions\":[\"enter\"],\"notes\":\"n\"}"
                        )
                    }
                }
            ]
        }

    schema = SchemaBundle(
        input_schema=None,
        output_schema={
            "type": "object",
            "properties": {
                "decision": {"type": "string"},
                "confidence": {"type": "number"},
                "rationale": {"type": "array"},
                "risk_checks": {"type": "array"},
                "recommended_actions": {"type": "array"},
                "notes": {"type": "string"},
            },
            "required": ["decision", "confidence", "rationale", "risk_checks", "recommended_actions", "notes"],
            "version": "v1",
        },
    )

    provider = OpenAIProvider(model="gpt-test", client=fake_client, json_mode=True)
    res = run_llm_task(
        task_name=LLMTaskName.TRADE_DECISION,
        raw_inputs={"symbol": "BTCUSDT"},
        provider=provider,
        schema_bundle=schema,
        options=OrchestrationOptions(enable_memory=False),
    )
    assert res.status == "success"
    assert res.final_output is not None
