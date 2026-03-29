````markdown
# TRADE REQUEST MANAGEMENT INTENT

## Main Intent
`trade_request_management`

---

## Description
Handles creation, retrieval, listing, cancellation, and validation of structured trade requests.  
These operations do not place any order on the exchange. They create and manage pre-execution trading requests stored in the local system.

---

## Sub-Intents

### 1. `trade_request_create`
Create a new structured trade request.

### 2. `trade_request_list`
List stored trade requests.

### 3. `trade_request_show`
Retrieve details of a specific trade request.

### 4. `trade_request_cancel`
Cancel a trade request that is still in cancellable state.

### 5. `trade_request_validate`
Validate a stored trade request against exchange rules and feasibility checks.

---

## Internal API Function Mapping

| Sub-Intent            | Function Name           |
|----------------------|-------------------------|
| trade_request_create | create_trade_request    |
| trade_request_list   | list_trade_requests     |
| trade_request_show   | get_trade_request       |
| trade_request_cancel | cancel_trade_request    |
| trade_request_validate | validate_trade_request |

---

## Function Specifications

---

### 1. create_trade_request

#### Description
Creates a structured trade request and stores it locally.  
This step does not place any order.

#### Function Signature
`create_trade_request(symbol, profit_target_pct, deadline, budget_mode, budget_amount=None, budget_asset="USDT", exit_asset="USDT", confirm=False)`

#### Parameters

| Name              | Type    | Required | Description |
|-------------------|---------|----------|------------|
| symbol            | string  | Yes      | Trading pair, e.g. BTCUSDT |
| profit_target_pct | number  | Yes      | Desired profit target percentage |
| deadline          | object  | Yes      | Requested deadline information |
| budget_mode       | string  | Yes      | Budget mode: `manual` or `auto` |
| budget_amount     | number  | No       | Budget amount, required when budget mode is `manual` |
| budget_asset      | string  | No       | Budget asset, default `USDT` |
| exit_asset        | string  | No       | Exit asset, default `USDT` |
| confirm           | boolean | No       | Optional explicit confirmation flag |

#### Deadline Object
```json
{
  "deadline_hours": 24
}
````

Alternative forms may be supported internally if your application supports them, but feasibility validation should ensure the required format is available.

#### Output

```json
{
  "trade_request_id": 12,
  "status": "NEW",
  "symbol": "BTCUSDT",
  "budget_mode": "manual",
  "budget_amount": 50,
  "budget_asset": "USDT",
  "profit_target_pct": 2.0
}
```

---

### 2. list_trade_requests

#### Description

Returns stored trade requests.

#### Function Signature

`list_trade_requests(limit=None)`

#### Parameters

| Name  | Type    | Required | Description               |
| ----- | ------- | -------- | ------------------------- |
| limit | integer | No       | Maximum number of results |

#### Output

```json id="2p7a2f"
{
  "items": [
    {
      "trade_request_id": 12,
      "symbol": "BTCUSDT",
      "status": "NEW",
      "validation_status": "PENDING"
    }
  ]
}
```

---

### 3. get_trade_request

#### Description

Returns a single trade request with stored details and latest validation state.

#### Function Signature

`get_trade_request(trade_request_id)`

#### Parameters

| Name             | Type    | Required | Description              |
| ---------------- | ------- | -------- | ------------------------ |
| trade_request_id | integer | Yes      | Trade request identifier |

#### Output

```json id="v2wd64"
{
  "trade_request_id": 12,
  "symbol": "BTCUSDT",
  "status": "NEW",
  "validation_status": "VALID",
  "profit_target_pct": 2.0,
  "deadline_hours": 24,
  "budget_mode": "manual",
  "budget_amount": 50,
  "budget_asset": "USDT",
  "exit_asset": "USDT"
}
```

---

### 4. cancel_trade_request

#### Description

Cancels a stored trade request if it is still cancellable.

#### Function Signature

`cancel_trade_request(trade_request_id)`

#### Parameters

| Name             | Type    | Required | Description              |
| ---------------- | ------- | -------- | ------------------------ |
| trade_request_id | integer | Yes      | Trade request identifier |

#### Output

```json id="uao7lx"
{
  "trade_request_id": 12,
  "status": "CANCELLED"
}
```

---

### 5. validate_trade_request

#### Description

Validates a stored trade request using exchange rules, current pricing, and feasibility checks.
This step does not place any order.

#### Function Signature

`validate_trade_request(trade_request_id)`

#### Parameters

| Name             | Type    | Required | Description              |
| ---------------- | ------- | -------- | ------------------------ |
| trade_request_id | integer | Yes      | Trade request identifier |

#### Behavior

* Checks exchange rules such as lot size and min notional
* Checks current market feasibility
* Stores validation result back into local database
* May estimate quantity

#### Output

```json id="kohvv2"
{
  "trade_request_id": 12,
  "validation_status": "VALID",
  "estimated_quantity": "0.0008",
  "reason": null
}
```

---

## Tool Calling Schema

### trade_request_create

```json id="rvqvdc"
{
  "name": "create_trade_request",
  "arguments": {
    "symbol": "BTCUSDT",
    "profit_target_pct": 2.0,
    "deadline": {
      "deadline_hours": 24
    },
    "budget_mode": "manual",
    "budget_amount": 50,
    "budget_asset": "USDT",
    "exit_asset": "USDT",
    "confirm": false
  }
}
```

---

### trade_request_list

```json id="5rq3uo"
{
  "name": "list_trade_requests",
  "arguments": {
    "limit": "optional integer"
  }
}
```

---

### trade_request_show

```json id="c14xi8"
{
  "name": "get_trade_request",
  "arguments": {
    "trade_request_id": 12
  }
}
```

---

### trade_request_cancel

```json id="ctr9d7"
{
  "name": "cancel_trade_request",
  "arguments": {
    "trade_request_id": 12
  }
}
```

---

### trade_request_validate

```json id="6siyd0"
{
  "name": "validate_trade_request",
  "arguments": {
    "trade_request_id": 12
  }
}
```

---

## Required Parameters Summary

### trade_request_create

Required:

* `symbol`
* `profit_target_pct`
* `deadline`
* `budget_mode`

Conditionally required:

* `budget_amount` when `budget_mode = "manual"`

Optional:

* `budget_asset`
* `exit_asset`
* `confirm`

### trade_request_list

Optional:

* `limit`

### trade_request_show

Required:

* `trade_request_id`

### trade_request_cancel

Required:

* `trade_request_id`

### trade_request_validate

Required:

* `trade_request_id`

---

## Validation Rules

* `symbol` must be a valid trading pair format
* `profit_target_pct` must be greater than zero
* `budget_mode` must be one of: `manual`, `auto`
* `budget_amount` is required when budget mode is `manual`
* `budget_amount` must be greater than zero when provided
* `trade_request_id` must reference an existing record
* cancellation is only allowed for requests in cancellable state
* validation requires all fields needed by feasibility logic
* if feasibility depends on `deadline_hours`, that value must be present and greater than zero

---

## Intent Routing Rules

* "create trade request", "start a trade request" → `trade_request_create`
* "list trade requests" → `trade_request_list`
* "show trade request 12" → `trade_request_show`
* "cancel trade request 12" → `trade_request_cancel`
* "validate trade request 12" → `trade_request_validate`

---

## Safety / Permission

| Sub-Intent             | Risk Level | Agent Allowed |
| ---------------------- | ---------- | ------------- |
| trade_request_create   | Low        | Yes           |
| trade_request_list     | Safe       | Yes           |
| trade_request_show     | Safe       | Yes           |
| trade_request_cancel   | Medium     | Yes           |
| trade_request_validate | Low        | Yes           |

---

## Notes

* These operations do not place any exchange order
* Validation is a gate, not execution
* Validation results should be stored and reused by later planning phases
* Trade requests should remain separate from execution candidates and executions

```
```
