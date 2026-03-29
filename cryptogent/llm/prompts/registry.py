from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cryptogent.llm.contracts import LLMTaskName, PromptTemplate


@dataclass(frozen=True)
class TemplateRef:
    template_key: str
    version: str


TEMPLATE_REGISTRY: dict[LLMTaskName, TemplateRef] = {
    LLMTaskName.INTENT_CLASSIFICATION: TemplateRef(template_key="intent_classification", version="v1"),
    LLMTaskName.NEWS_SUMMARY: TemplateRef(template_key="news_summary", version="v1"),
    LLMTaskName.MARKET_FINAL_ANALYSIS: TemplateRef(template_key="market_final_analysis", version="v1"),
    LLMTaskName.TRADE_DECISION: TemplateRef(template_key="trade_decision", version="v1"),
    LLMTaskName.RISK_EVALUATION: TemplateRef(template_key="risk_evaluation", version="v1"),
    LLMTaskName.MARKET_SENTIMENT_SYNTHESIS: TemplateRef(template_key="market_sentiment_synthesis", version="v1"),
    LLMTaskName.TRADE_RECOMMENDATION: TemplateRef(template_key="trade_recommendation", version="v1"),
    LLMTaskName.SAFETY_POLICY_REVIEW: TemplateRef(template_key="safety_policy_review", version="v1"),
    LLMTaskName.POSITION_SUMMARY: TemplateRef(template_key="position_summary", version="v1"),
    LLMTaskName.PORTFOLIO_RISK_SUMMARY: TemplateRef(template_key="portfolio_risk_summary", version="v1"),
    LLMTaskName.DECISION_EXPLANATION: TemplateRef(template_key="decision_explanation", version="v1"),
}


def get_prompt_template(task_name: LLMTaskName, version: str | None = None) -> PromptTemplate:
    ref = TEMPLATE_REGISTRY.get(task_name)
    if ref is None:
        raise ValueError(f"No prompt template registered for task {task_name}")
    chosen_version = version or ref.version
    base_dir = Path(__file__).resolve().parent
    template_path = base_dir / "templates" / ref.template_key / f"{chosen_version}.txt"
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    raw = template_path.read_text(encoding="utf-8")
    system_template, user_template = _split_template(raw)
    return PromptTemplate(
        name=f"{ref.template_key}:{chosen_version}",
        system_template=system_template,
        user_template=user_template,
        version=chosen_version,
    )


def _split_template(raw: str) -> tuple[str, str]:
    system_marker = "### SYSTEM"
    user_marker = "### USER"
    if system_marker in raw and user_marker in raw:
        system_part = raw.split(system_marker, 1)[1]
        system_text, user_part = system_part.split(user_marker, 1)
        return system_text.strip(), user_part.strip()
    return "", raw.strip()
