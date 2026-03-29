from cryptogent.llm.contracts import LLMTaskName, ParsedLLMResult, SchemaBundle
from cryptogent.llm.validators import ValidationContext, validate_result


def test_trade_decision_invalid_enum_rejected() -> None:
    parsed = ParsedLLMResult(
        task_name=LLMTaskName.TRADE_DECISION,
        content="{}",
        structured={"decision": "invalid", "confidence": 0.5, "rationale": ["x"]},
    )
    schema = SchemaBundle(
        input_schema=None,
        output_schema={
            "type": "object",
            "properties": {
                "decision": {"type": "string"},
                "confidence": {"type": "number"},
                "rationale": {"type": "array"},
            },
            "required": ["decision", "confidence", "rationale"],
        },
    )
    outcome = validate_result(parsed, ValidationContext(task_name=LLMTaskName.TRADE_DECISION, schema_bundle=schema))
    assert outcome.decision == "rejected"


def test_risk_evaluation_key_risks_warning() -> None:
    parsed = ParsedLLMResult(
        task_name=LLMTaskName.RISK_EVALUATION,
        content="{}",
        structured={"risk_level": "high", "confidence": 0.5},
    )
    schema = SchemaBundle(
        input_schema=None,
        output_schema={
            "type": "object",
            "properties": {
                "risk_level": {"type": "string"},
                "confidence": {"type": "number"},
            },
            "required": ["risk_level", "confidence"],
        },
    )
    outcome = validate_result(parsed, ValidationContext(task_name=LLMTaskName.RISK_EVALUATION, schema_bundle=schema))
    assert outcome.decision in ("accepted_with_warning", "accepted")
    assert "key_risks_required" in outcome.warnings
