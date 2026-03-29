from __future__ import annotations

from typing import Any

from cryptogent.llm.contracts import LLMTaskName


def validate_policy(task_name: LLMTaskName, data: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    confidence = data.get("confidence")
    if confidence is not None:
        try:
            c = float(confidence)
            if c < 0 or c > 1:
                errors.append("confidence_out_of_range")
        except Exception:
            errors.append("confidence_invalid")

    if task_name == LLMTaskName.TRADE_DECISION:
        _validate_trade_decision(data, errors, warnings)
    elif task_name == LLMTaskName.RISK_EVALUATION:
        _validate_risk_evaluation(data, errors, warnings)
    elif task_name == LLMTaskName.MARKET_FINAL_ANALYSIS:
        _validate_market_final_analysis(data, errors)
    elif task_name == LLMTaskName.MARKET_SENTIMENT_SYNTHESIS:
        _validate_market_sentiment(data, errors, warnings)
    elif task_name == LLMTaskName.NEWS_SUMMARY:
        _validate_news_summary(data, errors)

    return errors, warnings


def _validate_trade_decision(data: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    decision = str(data.get("decision") or "").lower()
    if decision not in ("buy", "sell", "hold", "no_trade"):
        errors.append("decision_invalid")
    symbol = data.get("symbol")
    if symbol is not None and not str(symbol).strip():
        errors.append("symbol_invalid")
    for key in ("budget", "budget_amount", "risk", "risk_amount"):
        if key in data:
            try:
                if float(data.get(key)) < 0:
                    errors.append(f"{key}_negative")
            except Exception:
                errors.append(f"{key}_invalid")
    for key in ("stop_loss_pct", "take_profit_pct"):
        if key in data:
            try:
                v = float(data.get(key))
                if v <= 0:
                    errors.append(f"{key}_invalid")
            except Exception:
                errors.append(f"{key}_invalid")
    rationale = data.get("rationale")
    if isinstance(rationale, list) and len(rationale) == 0:
        errors.append("rationale_empty")
    if rationale is None:
        warnings.append("rationale_missing")


def _validate_risk_evaluation(data: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    level = str(data.get("risk_level") or "").lower()
    if level not in ("low", "medium", "high"):
        errors.append("risk_level_invalid")
    key_risks = data.get("key_risks")
    if level in ("medium", "high"):
        if not isinstance(key_risks, list) or len(key_risks) == 0:
            warnings.append("key_risks_required")


def _validate_market_final_analysis(data: dict[str, Any], errors: list[str]) -> None:
    bias = str(data.get("market_bias") or "").lower()
    if bias and bias not in ("bullish", "neutral", "bearish"):
        errors.append("market_bias_invalid")
    summary = data.get("summary")
    if isinstance(summary, str) and not summary.strip():
        errors.append("summary_empty")


def _validate_market_sentiment(data: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    sentiment = str(data.get("sentiment") or "").lower()
    if sentiment and sentiment not in ("bullish", "neutral", "bearish"):
        errors.append("sentiment_invalid")
    drivers = data.get("drivers")
    if sentiment in ("bullish", "bearish"):
        if not isinstance(drivers, list) or len(drivers) == 0:
            warnings.append("drivers_required")


def _validate_news_summary(data: dict[str, Any], errors: list[str]) -> None:
    summary = data.get("summary")
    if isinstance(summary, str) and not summary.strip():
        errors.append("summary_empty")
    impact = str(data.get("impact") or "").lower()
    if impact and impact not in ("low", "medium", "high"):
        errors.append("impact_invalid")
