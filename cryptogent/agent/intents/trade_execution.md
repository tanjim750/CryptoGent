````markdown
# TRADE EXECUTION INTENT

## Main Intent
`trade_execution`

---

## Description
Handles execution of approved trade candidates, execution history retrieval, execution cancellation, and reconciliation of execution state with the exchange.  
These operations may submit or cancel real exchange orders depending on environment and confirmation policy.

---

## Sub-Intents

### 1. `trade_execute`
Execute an approved execution candidate.

### 2. `trade_execution_list`
List stored execution attempts.

### 3. `trade_execution_show`
Retrieve details of a specific execution attempt.

### 4. `trade_execution_cancel`
Cancel an open execution-backed limit order.

### 5. `trade_reconcile`
Reconcile tracked executions with exchange state.

### 6. `trade_reconcile_all`
Reconcile all tracked trade activity.

---

## Internal API Function Mapping

| Sub-Intent             | Function Name                |
|-----------------------|------------------------------|
| trade_execute         | execute_trade_candidate      |
| trade_execution_list  | list_trade_executions        |
| trade_execution_show  | get_trade_execution          |
| trade_execution_cancel| cancel_trade_execution       |
| trade_reconcile       | reconcile_trade_executions   |
| trade_reconcile_all   | reconcile_all_trade_activity |

---

## Function Specifications

---

### 1. execute_trade_candidate

#### Description
Executes an approved execution candidate and persists an execution record.  
This operation may place a real exchange order depending on the active environment.

#### Function Signature
`execute_trade_candidate(candidate_id, confirm=False)`

#### Parameters

| Name       | Type    | Required | Description |
|------------|---------|----------|------------|
| candidate_id| integer| Yes      | Execution candidate identifier |
| confirm    | boolean | No       | Explicit confirmation flag |

#### Behavior
- Loads execution candidate
- Verifies candidate is executable
- Submits exchange order
- Persists execution attempt
- Uses idempotent order submission strategy

#### Output
```json
{
  "execution_id": 51,
  "candidate_id": 34,
  "status": "SUBMITTED",
  "symbol": "BTCUSDT",
  "order_type": "MARKET_BUY",
  "client_order_id": "cg_exec_abc123"
}
````

---

### 2. list_trade_executions

#### Description

Returns stored execution attempts.

#### Function Signature

`list_trade_executions(limit=None)`

#### Parameters

| Name  | Type    | Required | Description               |
| ----- | ------- | -------- | ------------------------- |
| limit | integer | No       | Maximum number of results |

#### Output

```json id="iqs4wa"
{
  "items": [
    {
      "execution_id": 51,
      "candidate_id": 34,
      "symbol": "BTCUSDT",
      "status": "FILLED"
    }
  ]
}
```

---

### 3. get_trade_execution

#### Description

Returns a specific execution attempt with stored exchange and reconciliation details.

#### Function Signature

`get_trade_execution(execution_id)`

#### Parameters

| Name         | Type    | Required | Description          |
| ------------ | ------- | -------- | -------------------- |
| execution_id | integer | Yes      | Execution identifier |

#### Output

```json id="sf87ld"
{
  "execution_id": 51,
  "candidate_id": 34,
  "symbol": "BTCUSDT",
  "order_type": "MARKET_BUY",
  "status": "FILLED",
  "client_order_id": "cg_exec_abc123",
  "executed_quantity": "0.0008",
  "avg_fill_price": "62000"
}
```

---

### 4. cancel_trade_execution

#### Description

Cancels an open limit execution on the exchange and updates local state.

#### Function Signature

`cancel_trade_execution(execution_id, confirm=False)`

#### Parameters

| Name         | Type    | Required | Description                |
| ------------ | ------- | -------- | -------------------------- |
| execution_id | integer | Yes      | Execution identifier       |
| confirm      | boolean | No       | Explicit confirmation flag |

#### Behavior

* Loads stored execution
* Verifies cancellation is applicable
* Sends cancel request to exchange
* Refreshes local open orders and position lock state

#### Output

```json id="3ydov7"
{
  "execution_id": 51,
  "status": "CANCELLED"
}
```

---

### 5. reconcile_trade_executions

#### Description

Reconciles tracked executions with exchange order state, including uncertain or open executions.

#### Function Signature

`reconcile_trade_executions(limit_order_timeout_minutes=30, auto_cancel_expired=False, confirm=False)`

#### Parameters

| Name                        | Type    | Required | Description                                         |
| --------------------------- | ------- | -------- | --------------------------------------------------- |
| limit_order_timeout_minutes | integer | No       | Local timeout for open limit orders                 |
| auto_cancel_expired         | boolean | No       | Automatically cancel expired limit orders           |
| confirm                     | boolean | No       | Explicit confirmation flag for auto-cancel behavior |

#### Behavior

* Queries exchange by stored client order identifiers
* Updates local execution state
* Marks timed-out limit orders as locally expired
* Optionally cancels expired orders on exchange

#### Output

```json id="11jixx"
{
  "status": "success",
  "reconciled_count": 4,
  "expired_count": 1,
  "cancelled_count": 0
}
```

---

### 6. reconcile_all_trade_activity

#### Description

Runs broader reconciliation across executions, manual-tracked activity, and cached open orders.

#### Function Signature

`reconcile_all_trade_activity()`

#### Parameters

None

#### Behavior

* Reconciles stored executions
* Reconciles tracked manual order records where applicable
* Reconciles cached open orders progressively

#### Output

```json id="7gsx0c"
{
  "status": "success",
  "executions_reconciled": 4,
  "open_orders_reconciled": 7
}
```

---

## Tool Calling Schema

### trade_execute

```json id="4cwhsq"
{
  "name": "execute_trade_candidate",
  "arguments": {
    "candidate_id": 34,
    "confirm": false
  }
}
```

---

### trade_execution_list

```json id="q4k4if"
{
  "name": "list_trade_executions",
  "arguments": {
    "limit": "optional integer"
  }
}
```

---

### trade_execution_show

```json id="vq0ivp"
{
  "name": "get_trade_execution",
  "arguments": {
    "execution_id": 51
  }
}
```

---

### trade_execution_cancel

```json id="jb4x29"
{
  "name": "cancel_trade_execution",
  "arguments": {
    "execution_id": 51,
    "confirm": false
  }
}
```

---

### trade_reconcile

```json id="v3qlmq"
{
  "name": "reconcile_trade_executions",
  "arguments": {
    "limit_order_timeout_minutes": 30,
    "auto_cancel_expired": false,
    "confirm": false
  }
}
```

---

### trade_reconcile_all

```json id="gd1usj"
{
  "name": "reconcile_all_trade_activity",
  "arguments": {}
}
```

---

## Required Parameters Summary

### trade_execute

Required:

* `candidate_id`

Optional:

* `confirm`

### trade_execution_list

Optional:

* `limit`

### trade_execution_show

Required:

* `execution_id`

### trade_execution_cancel

Required:

* `execution_id`

Optional:

* `confirm`

### trade_reconcile

Optional:

* `limit_order_timeout_minutes`
* `auto_cancel_expired`
* `confirm`

### trade_reconcile_all

No parameters required

---

## Validation Rules

* `candidate_id` must reference an existing approved execution candidate
* candidate must be in executable state
* execution must respect current environment and policy gates
* `execution_id` must reference an existing execution record
* cancellation applies only to cancelable exchange-backed limit executions
* `limit_order_timeout_minutes` must be a positive integer if provided
* auto-cancel behavior must respect confirmation policy
* reconciliation must preserve idempotency and not duplicate executions

---

## Intent Routing Rules

* "execute candidate 34" → `trade_execute`
* "list executions" → `trade_execution_list`
* "show execution 51" → `trade_execution_show`
* "cancel execution 51" → `trade_execution_cancel`
* "reconcile executions" → `trade_reconcile`
* "reconcile all trade activity" → `trade_reconcile_all`

---

## Safety / Permission

| Sub-Intent             | Risk Level | Agent Allowed                 |
| ---------------------- | ---------- | ----------------------------- |
| trade_execute          | High       | Yes, with confirmation policy |
| trade_execution_list   | Safe       | Yes                           |
| trade_execution_show   | Safe       | Yes                           |
| trade_execution_cancel | High       | Yes, with confirmation policy |
| trade_reconcile        | Medium     | Yes                           |
| trade_reconcile_all    | Medium     | Yes                           |

---

## Notes

* These operations can have real exchange side effects
* Execution should only be allowed for approved candidates
* Confirmation policy should be applied before execution and cancellation
* Reconciliation is critical for recovering uncertain or stale local execution state

```
```
