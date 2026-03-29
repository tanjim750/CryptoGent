````markdown
# TRADE PLANNING INTENT

## Main Intent
`trade_planning`

---

## Description
Handles deterministic trade plan generation, plan retrieval, safety validation, and execution candidate preparation.  
These operations do not place any order on the exchange. They convert validated trade requests into structured plans and safe execution candidates.

---

## Sub-Intents

### 1. `trade_plan_build`
Build a deterministic trade plan from a validated trade request.

### 2. `trade_plan_list`
List stored trade plans.

### 3. `trade_plan_show`
Retrieve details of a specific trade plan.

### 4. `trade_safety_check`
Run safety validation on a trade plan and generate an execution candidate.

### 5. `execution_candidate_generate`
Generate an execution candidate from a plan and safety options.

### 6. `execution_candidate_review`
Retrieve details of a specific execution candidate.

---

## Internal API Function Mapping

| Sub-Intent                  | Function Name                 |
|----------------------------|-------------------------------|
| trade_plan_build           | build_trade_plan              |
| trade_plan_list            | list_trade_plans              |
| trade_plan_show            | get_trade_plan                |
| trade_safety_check         | run_trade_safety_validation   |
| execution_candidate_generate | generate_execution_candidate |
| execution_candidate_review | get_execution_candidate       |

---

## Function Specifications

---

### 1. build_trade_plan

#### Description
Builds and stores a deterministic trade plan from a previously validated trade request.  
This step does not place any order.

#### Function Signature
`build_trade_plan(trade_request_id)`

#### Parameters

| Name             | Type    | Required | Description |
|------------------|---------|----------|------------|
| trade_request_id | integer | Yes      | Trade request identifier |

#### Behavior
- Requires the referenced trade request to be valid
- Uses public market data, rules snapshot, and sizing logic
- Persists a trade plan in local storage

#### Output
```json
{
  "plan_id": 21,
  "trade_request_id": 12,
  "status": "BUILT",
  "symbol": "BTCUSDT",
  "candidate_count": 1
}
````

---

### 2. list_trade_plans

#### Description

Returns stored trade plans.

#### Function Signature

`list_trade_plans(limit=None)`

#### Parameters

| Name  | Type    | Required | Description               |
| ----- | ------- | -------- | ------------------------- |
| limit | integer | No       | Maximum number of results |

#### Output

```json id="6m3hsd"
{
  "items": [
    {
      "plan_id": 21,
      "trade_request_id": 12,
      "symbol": "BTCUSDT",
      "status": "BUILT"
    }
  ]
}
```

---

### 3. get_trade_plan

#### Description

Returns a specific stored trade plan including rules snapshot and candidate summary.

#### Function Signature

`get_trade_plan(plan_id)`

#### Parameters

| Name    | Type    | Required | Description           |
| ------- | ------- | -------- | --------------------- |
| plan_id | integer | Yes      | Trade plan identifier |

#### Output

```json id="0jddhm"
{
  "plan_id": 21,
  "trade_request_id": 12,
  "symbol": "BTCUSDT",
  "status": "BUILT",
  "rules_snapshot": {
    "min_notional": "10",
    "step_size": "0.000001"
  },
  "candidates": [
    {
      "order_type": "MARKET_BUY",
      "approved_budget_amount": "50"
    }
  ]
}
```

---

### 4. run_trade_safety_validation

#### Description

Runs safety validation on a stored trade plan and persists an execution candidate.
This step does not place any order.

#### Function Signature

`run_trade_safety_validation(plan_id, order_type=None, limit_price=None, position_id=None, close_mode=None, close_amount=None, close_percent=None)`

#### Parameters

| Name          | Type    | Required | Description                           |
| ------------- | ------- | -------- | ------------------------------------- |
| plan_id       | integer | Yes      | Trade plan identifier                 |
| order_type    | string  | No       | Candidate order type                  |
| limit_price   | number  | No       | Required for limit orders             |
| position_id   | integer | No       | Position identifier for sell flows    |
| close_mode    | string  | No       | `amount`, `percent`, or `all`         |
| close_amount  | number  | No       | Required when close_mode is `amount`  |
| close_percent | number  | No       | Required when close_mode is `percent` |

#### Supported Order Types

* `MARKET_BUY`
* `LIMIT_BUY`
* `MARKET_SELL`
* `LIMIT_SELL`

#### Behavior

* Validates sizing, risk bounds, and exchange constraints
* Generates a persistent execution candidate
* Supports buy-side and sell-side candidate generation

#### Output

```json id="10v8c0"
{
  "candidate_id": 34,
  "plan_id": 21,
  "status": "APPROVED",
  "order_type": "MARKET_BUY",
  "symbol": "BTCUSDT"
}
```

---

### 5. generate_execution_candidate

#### Description

Generates an execution candidate from a plan using explicit safety options.
This is typically a wrapper around safety validation logic.

#### Function Signature

`generate_execution_candidate(plan_id, safety_options)`

#### Parameters

| Name           | Type    | Required | Description                  |
| -------------- | ------- | -------- | ---------------------------- |
| plan_id        | integer | Yes      | Trade plan identifier        |
| safety_options | object  | Yes      | Candidate generation options |

#### Example Safety Options

```json id="ccbx6d"
{
  "order_type": "LIMIT_BUY",
  "limit_price": 59000
}
```

#### Output

```json id="dgo7q5"
{
  "candidate_id": 34,
  "plan_id": 21,
  "status": "APPROVED",
  "order_type": "LIMIT_BUY"
}
```

---

### 6. get_execution_candidate

#### Description

Returns details of a specific execution candidate.

#### Function Signature

`get_execution_candidate(candidate_id)`

#### Parameters

| Name         | Type    | Required | Description                    |
| ------------ | ------- | -------- | ------------------------------ |
| candidate_id | integer | Yes      | Execution candidate identifier |

#### Output

```json id="85n2la"
{
  "candidate_id": 34,
  "plan_id": 21,
  "symbol": "BTCUSDT",
  "order_type": "MARKET_BUY",
  "status": "APPROVED",
  "approved_budget_amount": "50",
  "estimated_quantity": "0.0008"
}
```

---

## Tool Calling Schema

### trade_plan_build

```json id="jlwm9r"
{
  "name": "build_trade_plan",
  "arguments": {
    "trade_request_id": 12
  }
}
```

---

### trade_plan_list

```json id="m5y6lb"
{
  "name": "list_trade_plans",
  "arguments": {
    "limit": "optional integer"
  }
}
```

---

### trade_plan_show

```json id="991ca1"
{
  "name": "get_trade_plan",
  "arguments": {
    "plan_id": 21
  }
}
```

---

### trade_safety_check

```json id="b98ptx"
{
  "name": "run_trade_safety_validation",
  "arguments": {
    "plan_id": 21,
    "order_type": "MARKET_BUY",
    "limit_price": "optional number",
    "position_id": "optional integer",
    "close_mode": "optional string",
    "close_amount": "optional number",
    "close_percent": "optional number"
  }
}
```

---

### execution_candidate_generate

```json id="f0ie1i"
{
  "name": "generate_execution_candidate",
  "arguments": {
    "plan_id": 21,
    "safety_options": {
      "order_type": "LIMIT_BUY",
      "limit_price": 59000
    }
  }
}
```

---

### execution_candidate_review

```json id="6i58wq"
{
  "name": "get_execution_candidate",
  "arguments": {
    "candidate_id": 34
  }
}
```

---

## Required Parameters Summary

### trade_plan_build

Required:

* `trade_request_id`

### trade_plan_list

Optional:

* `limit`

### trade_plan_show

Required:

* `plan_id`

### trade_safety_check

Required:

* `plan_id`

Conditionally required:

* `limit_price` for `LIMIT_BUY` and `LIMIT_SELL`
* `close_mode` for sell-side candidate generation when needed
* `close_amount` when `close_mode = "amount"`
* `close_percent` when `close_mode = "percent"`

Optional:

* `order_type`
* `position_id`

### execution_candidate_generate

Required:

* `plan_id`
* `safety_options`

### execution_candidate_review

Required:

* `candidate_id`

---

## Validation Rules

* `trade_request_id` must reference an existing validated trade request
* `plan_id` must reference an existing trade plan
* `candidate_id` must reference an existing execution candidate
* `order_type` must be one of:

  * `MARKET_BUY`
  * `LIMIT_BUY`
  * `MARKET_SELL`
  * `LIMIT_SELL`
* `limit_price` is required for all limit order types
* `close_mode` must be one of: `amount`, `percent`, `all`
* `close_amount` is required when `close_mode = "amount"`
* `close_percent` is required when `close_mode = "percent"`
* `position_id` should be valid when sell-side flow needs explicit position targeting
* safety validation must enforce lot size, min notional, and policy constraints

---

## Intent Routing Rules

* "build trade plan", "plan build for request 12" → `trade_plan_build`
* "list trade plans" → `trade_plan_list`
* "show trade plan 21" → `trade_plan_show`
* "run safety on plan 21" → `trade_safety_check`
* "generate execution candidate for plan 21" → `execution_candidate_generate`
* "show candidate 34" → `execution_candidate_review`

---

## Safety / Permission

| Sub-Intent                   | Risk Level | Agent Allowed |
| ---------------------------- | ---------- | ------------- |
| trade_plan_build             | Low        | Yes           |
| trade_plan_list              | Safe       | Yes           |
| trade_plan_show              | Safe       | Yes           |
| trade_safety_check           | Low        | Yes           |
| execution_candidate_generate | Low        | Yes           |
| execution_candidate_review   | Safe       | Yes           |

---

## Notes

* These operations do not place any exchange order
* Trade planning is deterministic and separate from execution
* Safety validation is a gate before execution
* Execution candidates should be treated as pre-execution artifacts, not executed orders

```
```
