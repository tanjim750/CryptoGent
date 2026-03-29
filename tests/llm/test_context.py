from cryptogent.llm.context import ContextManager
from cryptogent.llm.contracts import LLMTaskName


def test_context_manager_news_summary_normalizes() -> None:
    ctx = ContextManager().build(
        task_name=LLMTaskName.NEWS_SUMMARY,
        raw_inputs={
            "title": "ETF approved",
            "symbols": "btc",
            "published_at_utc": "2026-03-01T00:00:00Z",
        },
    )
    assert ctx.task_name == LLMTaskName.NEWS_SUMMARY
    assert ctx.inputs.get("headline") == "ETF approved"
    assert ctx.inputs.get("symbols") == ["BTC"]
