````markdown id="market_intelligence_md"
# MARKET INTELLIGENCE INTENT

## Main Intent
`market_intelligence`

---

## Description
Handles all market-related analysis including news, sentiment, technical context, asset ranking, and opportunity discovery.  
This intent uses internal data pipelines (news, social, market data) and LLM-assisted synthesis to generate structured market insights.

---

## Sub-Intents

### 1. `market_analysis`
Full market analysis using news, sentiment, and technical data.

### 2. `market_overview`
High-level summary of current market condition.

### 3. `market_sentiment_summary`
Aggregated sentiment analysis from news and social sources.

### 4. `market_opportunity_discovery`
Identify best potential trading opportunities.

### 5. `asset_analysis`
Analyze a specific asset (e.g., BTCUSDT).

### 6. `asset_comparison`
Compare multiple assets.

### 7. `asset_ranking`
Rank assets based on signals.

### 8. `risk_assessment`
Evaluate risk for asset or plan.

### 9. `market_status_query`
Fetch structured market status (price, indicators, etc.).

### 10. `market_snapshot_list_query`
List stored market snapshots.

### 11. `market_snapshot_show`
Retrieve a specific snapshot.

---

## Internal API Function Mapping

| Sub-Intent                     | Function Name                          |
|-------------------------------|----------------------------------------|
| market_analysis               | run_market_analysis                    |
| market_overview               | get_market_overview                    |
| market_sentiment_summary      | get_market_sentiment_summary           |
| market_opportunity_discovery  | discover_trade_opportunities           |
| asset_analysis                | analyze_asset                          |
| asset_comparison              | compare_assets                         |
| asset_ranking                 | rank_assets                            |
| risk_assessment               | assess_asset_or_plan_risk              |
| market_status_query           | get_market_status                      |
| market_snapshot_list_query    | list_market_snapshots                  |
| market_snapshot_show          | get_market_snapshot                    |

---

## Function Specifications

---

### 1. run_market_analysis

#### Description
Runs full internal market intelligence pipeline (news → dedup → ranking → summarization → synthesis → decision).

#### Function Signature
`run_market_analysis(request_context)`

#### Parameters

| Name            | Type   | Required | Description |
|-----------------|--------|----------|------------|
| request_context | object | Yes      | Contains user intent, preferences, filters |

#### Output
```json
{
  "market_bias": "bullish",
  "confidence": 0.72,
  "top_assets": ["BTCUSDT", "ETHUSDT"],
  "risks": ["high volatility"],
  "summary": "Market shows upward momentum with mixed sentiment."
}
````

---

### 2. get_market_overview

#### Description

Returns a simplified high-level market summary.

#### Function Signature

`get_market_overview(request_context)`

---

### 3. get_market_sentiment_summary

#### Description

Returns aggregated sentiment derived from news and social sources.

#### Function Signature

`get_market_sentiment_summary(request_context)`

---

### 4. discover_trade_opportunities

#### Description

Identifies top trade candidates based on combined signals.

#### Function Signature

`discover_trade_opportunities(request_context)`

---

### 5. analyze_asset

#### Description

Performs deep analysis on a specific asset.

#### Function Signature

`analyze_asset(symbol, request_context)`

#### Parameters

| Name   | Type   | Required | Description                  |
| ------ | ------ | -------- | ---------------------------- |
| symbol | string | Yes      | Trading pair (e.g., BTCUSDT) |

---

### 6. compare_assets

#### Description

Compares multiple assets.

#### Function Signature

`compare_assets(symbols, request_context)`

#### Parameters

| Name    | Type  | Required | Description     |
| ------- | ----- | -------- | --------------- |
| symbols | array | Yes      | List of symbols |

---

### 7. rank_assets

#### Description

Ranks assets based on signals.

#### Function Signature

`rank_assets(symbols=None, request_context=None)`

---

### 8. assess_asset_or_plan_risk

#### Description

Evaluates risk for an asset or trade plan.

#### Function Signature

`assess_asset_or_plan_risk(symbol=None, plan_id=None, request_context=None)`

---

### 9. get_market_status

#### Description

Returns structured technical and price data.

#### Function Signature

`get_market_status(symbol, timeframe, profile_options)`

#### Parameters

| Name            | Type   | Required | Description              |
| --------------- | ------ | -------- | ------------------------ |
| symbol          | string | Yes      | Trading pair             |
| timeframe       | string | Yes      | Timeframe (e.g., 1h, 4h) |
| profile_options | object | No       | Indicator selection      |

---

### 10. list_market_snapshots

#### Description

Lists stored market snapshots.

#### Function Signature

`list_market_snapshots(limit=None, symbol=None, timeframe=None)`

---

### 11. get_market_snapshot

#### Description

Returns a specific stored snapshot.

#### Function Signature

`get_market_snapshot(snapshot_id)`

---

## Tool Calling Schema

### market_analysis

```json id="h1g4ks"
{
  "name": "run_market_analysis",
  "arguments": {
    "request_context": {}
  }
}
```

---

### asset_analysis

```json id="d7pl3m"
{
  "name": "analyze_asset",
  "arguments": {
    "symbol": "BTCUSDT",
    "request_context": {}
  }
}
```

---

### asset_ranking

```json id="u9av2k"
{
  "name": "rank_assets",
  "arguments": {
    "symbols": ["BTCUSDT", "ETHUSDT"]
  }
}
```

---

### market_status_query

```json id="k4sn8p"
{
  "name": "get_market_status",
  "arguments": {
    "symbol": "BTCUSDT",
    "timeframe": "1h"
  }
}
```

---

## Internal Hidden Workflow APIs

These are not directly exposed but used internally:

* plan_market_search_queries(request_context)
* build_provider_queries(canonical_query_plan)
* fetch_market_news(provider_queries)
* normalize_market_news(raw_items)
* deduplicate_market_news(normalized_items)
* rank_market_news(deduped_items, top_k)
* clean_market_news(items)
* chunk_market_news(items, token_budget)
* summarize_market_chunks(chunks)
* synthesize_market_sentiment(chunk_summaries)
* assemble_market_analysis_context(...)
* generate_market_analysis_decision(context)
* validate_market_analysis_decision(llm, deterministic)

---

## Validation Rules

* `symbol` must be valid trading pair
* `symbols` must be non-empty list
* `timeframe` must be supported value
* request_context must be structured object

---

## Intent Routing Rules

* "market analysis", "analyze market" → `market_analysis`
* "market overview" → `market_overview`
* "sentiment" → `market_sentiment_summary`
* "best coin", "opportunity" → `market_opportunity_discovery`
* "analyze BTC" → `asset_analysis`
* "compare BTC ETH" → `asset_comparison`
* "rank coins" → `asset_ranking`
* "risk of BTC" → `risk_assessment`
* "market status BTC 1h" → `market_status_query`

---

## Safety / Permission

| Sub-Intent                   | Risk Level | Agent Allowed |
| ---------------------------- | ---------- | ------------- |
| market_analysis              | Safe       | Yes           |
| market_overview              | Safe       | Yes           |
| market_sentiment_summary     | Safe       | Yes           |
| market_opportunity_discovery | Safe       | Yes           |
| asset_analysis               | Safe       | Yes           |
| asset_comparison             | Safe       | Yes           |
| asset_ranking                | Safe       | Yes           |
| risk_assessment              | Safe       | Yes           |
| market_status_query          | Safe       | Yes           |
| market_snapshot_list_query   | Safe       | Yes           |
| market_snapshot_show         | Safe       | Yes           |

---

## Notes

* Uses multi-step internal pipeline
* LLM output is advisory only
* Deterministic validation applied before trading decisions

```
```
