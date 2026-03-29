````markdown
# AGENTIC ROUTING DESIGN

---

## Description
Defines how the system routes user requests through a two-layer agentic architecture:

1. **High-Level Orchestrator (User Layer)**
2. **Execution Orchestrator (Internal Layer)**

This ensures clean separation between:
- intent understanding
- execution planning
- tool/API invocation

---

## Architecture Overview

```text
User Input
   ↓
High-Level Orchestrator
   ↓
Intent + Entity Extraction
   ↓
Routing Decision
   ↓
Execution Orchestrator (Workflow Engine)
   ↓
Tool/API Calls
   ↓
Structured Result
   ↓
High-Level Orchestrator
   ↓
Final Response
````

---

## Layer 1: High-Level Orchestrator

### Responsibilities

* Classify main intent
* Detect sub-intents
* Extract entities (symbol, ids, params)
* Handle direct/general questions
* Route to execution workflows
* Combine multi-step workflows
* Build final response

---

## Core APIs

### classify_user_intent

```text
classify_user_intent(user_message, conversation_context) → intent_result
```

#### Output

```json
{
  "main_intent": "trade_request_management",
  "sub_intents": ["trade_request_create", "trade_request_validate"],
  "confidence": 0.92
}
```

---

### extract_request_entities

```text
extract_request_entities(user_message, conversation_context) → entity_result
```

#### Output

```json
{
  "symbol": "BTCUSDT",
  "profit_target_pct": 2.0,
  "deadline_hours": 24,
  "budget_mode": "manual",
  "budget_amount": 50
}
```

---

### decide_routing_strategy

```text
decide_routing_strategy(intent_result, entity_result) → routing_plan
```

#### Output

```json
{
  "workflow": "multi_step",
  "steps": [
    "trade_request_create",
    "trade_request_validate"
  ]
}
```

---

### handle_direct_response

```text
handle_direct_response(user_message) → response
```

Used when:

* no tool needed
* general explanation
* knowledge query

---

### build_user_response

```text
build_user_response(workflow_results, conversation_context) → response
```

---

## Routing Types

### 1. Direct Response

No workflow execution required

Example:

* "what is stop loss?"

---

### 2. Single-Step Execution

One sub-intent → one function

Example:

* "show my positions"

---

### 3. Multi-Step Execution

Sequential workflow

Example:

* "create trade and validate"

---

### 4. Conditional Routing

Depends on intermediate result

Example:

* if validation = VALID → proceed to planning

---

### 5. Hybrid Routing

LLM + tool mix

Example:

* market analysis → fetch + summarize + respond

---

## Layer 2: Execution Orchestrator

---

## Responsibilities

* Translate sub-intents into function calls
* Execute workflows step-by-step
* Manage dependencies between steps
* Handle retries and failures
* Return structured outputs

---

## Core APIs

### execute_workflow

```text
execute_workflow(routing_plan, entity_result, context) → workflow_result
```

---

### execute_step

```text
execute_step(sub_intent, parameters) → step_result
```

---

### resolve_parameters

```text
resolve_parameters(sub_intent, entity_result, previous_results) → final_params
```

---

### handle_step_failure

```text
handle_step_failure(step_result) → retry | abort | fallback
```

---

## Workflow Execution Model

```text
for step in routing_plan.steps:
    params = resolve_parameters(step)
    result = execute_step(step, params)
    if failure:
        handle_step_failure()
    store result
return aggregated_result
```

---

## Parameter Resolution Strategy

Priority order:

1. Explicit user input
2. Extracted entities
3. Previous step output
4. Default values

---

## Example

User:
"Create BTC trade and validate it"

### Step 1: Intent

```json
{
  "main_intent": "trade_request_management",
  "sub_intents": [
    "trade_request_create",
    "trade_request_validate"
  ]
}
```

---

### Step 2: Routing Plan

```json
{
  "workflow": "multi_step",
  "steps": [
    "trade_request_create",
    "trade_request_validate"
  ]
}
```

---

### Step 3: Execution

#### Step 1 → create

Output:

```json
{
  "trade_request_id": 12
}
```

#### Step 2 → validate

Input:

```json
{
  "trade_request_id": 12
}
```

---

## Market Intelligence Special Routing

### Trigger

* `market_analysis`
* `asset_analysis`
* `asset_ranking`

---

### Flow

```text
High-Level Orchestrator
   ↓
Execution Orchestrator
   ↓
Internal Market Workflow
   ↓
Search Planning
   ↓
Provider Query Generation
   ↓
Data Fetch
   ↓
Normalization
   ↓
Deduplication
   ↓
Top-K Ranking
   ↓
Cleaning
   ↓
Chunking
   ↓
LLM Summarization
   ↓
Sentiment Synthesis
   ↓
Final Structured Output
```

---

## Internal Workflow APIs

* plan_market_search_queries
* build_provider_queries
* fetch_market_news
* normalize_market_news
* deduplicate_market_news
* rank_market_news
* clean_market_news
* chunk_market_news
* summarize_market_chunks
* synthesize_market_sentiment
* assemble_market_analysis_context
* generate_market_analysis_decision
* validate_market_analysis_decision

---

## Safety Layer (Global)

### Rules

* Manual intents → block execution
* High-risk intents → require confirmation
* Execution requires:

  * approved candidate
  * valid state
  * correct environment

---

## Confirmation Policy

| Intent Type     | Requires Confirmation |
| --------------- | --------------------- |
| config change   | Yes                   |
| trade execution | Yes                   |
| cancel order    | Yes                   |
| manual actions  | Always                |

---

## Fallback Strategy

### Cases

* missing parameters
* invalid state
* API failure

### Actions

* ask user for clarification
* retry with adjusted parameters
* fallback to safe response

---

## Memory Usage

### Conversation Context

* last intent
* last ids (trade_request_id, plan_id, etc.)
* last symbol

### Example

User:
"validate it"

System resolves:
→ previous trade_request_id

---

## Final Output Contract

All workflows must return structured output:

```json
{
  "status": "success | error",
  "data": {},
  "message": "optional",
  "next_possible_actions": []
}
```

---

## Summary

* Layer 1 = Intent + Routing
* Layer 2 = Execution + Tools
* Clear separation of responsibility
* Supports multi-step, conditional, and hybrid workflows
* Ensures safe and deterministic execution

```
```
