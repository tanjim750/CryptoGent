````markdown
# PNL MANAGEMENT INTENT

## Main Intent
`pnl_management`

---

## Description
Handles realized and unrealized profit and loss (PnL) queries.  
These operations are read-only and compute or retrieve PnL based on stored executions and positions, optionally using live market data.

---

## Sub-Intents

### 1. `realized_pnl_query`
List realized PnL from completed sell executions.

### 2. `realized_pnl_show`
Retrieve detailed realized PnL for a specific execution.

### 3. `unrealized_pnl_query`
Compute unrealized PnL using live market data.

### 4. `unrealized_pnl_static_query`
Return unrealized PnL without fetching live market data.

---

## Internal API Function Mapping

| Sub-Intent                 | Function Name                |
|---------------------------|------------------------------|
| realized_pnl_query        | list_realized_pnl            |
| realized_pnl_show         | get_realized_pnl_details     |
| unrealized_pnl_query      | list_unrealized_pnl          |
| unrealized_pnl_static_query | list_unrealized_pnl        |

---

## Function Specifications

---

### 1. list_realized_pnl

#### Description
Returns realized PnL from sell executions stored in the system.

#### Function Signature
`list_realized_pnl(limit=None)`

#### Parameters

| Name  | Type    | Required | Description |
|-------|---------|----------|------------|
| limit | integer | No       | Maximum number of results |

#### Output
```json
{
  "items": [
    {
      "execution_id": 51,
      "symbol": "BTCUSDT",
      "realized_pnl_quote": "2.15",
      "timestamp": "2026-03-24T10:10:00Z"
    }
  ]
}
````

---

### 2. get_realized_pnl_details

#### Description

Returns detailed realized PnL breakdown for a specific execution.

#### Function Signature

`get_realized_pnl_details(execution_id)`

#### Parameters

| Name         | Type    | Required | Description          |
| ------------ | ------- | -------- | -------------------- |
| execution_id | integer | Yes      | Execution identifier |

#### Output

```json id="4d2h1q"
{
  "execution_id": 51,
  "symbol": "BTCUSDT",
  "realized_pnl_quote": "2.15",
  "entry_price": "60000",
  "exit_price": "62000",
  "quantity": "0.001",
  "fees": {
    "amount": "0.02",
    "asset": "USDT"
  },
  "warnings": []
}
```

---

### 3. list_unrealized_pnl

#### Description

Returns unrealized PnL for open positions.
Can optionally fetch live prices.

#### Function Signature

`list_unrealized_pnl(position_id=None, limit=None, live=True)`

#### Parameters

| Name        | Type    | Required | Description                  |
| ----------- | ------- | -------- | ---------------------------- |
| position_id | integer | No       | Specific position identifier |
| limit       | integer | No       | Maximum number of results    |
| live        | boolean | No       | Whether to fetch live prices |

#### Output (Live)

```json id="l8y6pk"
{
  "items": [
    {
      "position_id": 9,
      "symbol": "BTCUSDT",
      "entry_price": "62000",
      "live_price": "62850",
      "quantity": "0.0012",
      "unrealized_pnl_quote": "1.02"
    }
  ]
}
```

#### Output (Static)

```json id="3jph6v"
{
  "items": [
    {
      "position_id": 9,
      "symbol": "BTCUSDT",
      "entry_price": "62000",
      "quantity": "0.0012"
    }
  ]
}
```

---

## Tool Calling Schema

### realized_pnl_query

```json id="5i1dqt"
{
  "name": "list_realized_pnl",
  "arguments": {
    "limit": "optional integer"
  }
}
```

---

### realized_pnl_show

```json id="z9ok0v"
{
  "name": "get_realized_pnl_details",
  "arguments": {
    "execution_id": 51
  }
}
```

---

### unrealized_pnl_query

```json id="ytnv6l"
{
  "name": "list_unrealized_pnl",
  "arguments": {
    "position_id": "optional integer",
    "limit": "optional integer",
    "live": true
  }
}
```

---

### unrealized_pnl_static_query

```json id="z6q7xw"
{
  "name": "list_unrealized_pnl",
  "arguments": {
    "position_id": "optional integer",
    "limit": "optional integer",
    "live": false
  }
}
```

---

## Required Parameters Summary

### realized_pnl_query

Optional:

* `limit`

### realized_pnl_show

Required:

* `execution_id`

### unrealized_pnl_query

Optional:

* `position_id`
* `limit`
* `live` (default true)

### unrealized_pnl_static_query

Optional:

* `position_id`
* `limit`
* `live=false`

---

## Validation Rules

* `execution_id` must reference an existing execution
* `position_id` must reference an existing position when provided
* `limit` must be a positive integer if provided
* `live` must be boolean
* unrealized PnL must be computed using consistent Decimal-safe arithmetic
* fee handling must be included in realized PnL where available
* warnings should be included if fee asset differs or data is incomplete

---

## Intent Routing Rules

* "realized pnl", "profit history" → `realized_pnl_query`
* "show pnl for execution 51" → `realized_pnl_show`
* "unrealized pnl", "current profit" → `unrealized_pnl_query`
* "static pnl", "pnl without live data" → `unrealized_pnl_static_query`

---

## Safety / Permission

| Sub-Intent                  | Risk Level | Agent Allowed |
| --------------------------- | ---------- | ------------- |
| realized_pnl_query          | Safe       | Yes           |
| realized_pnl_show           | Safe       | Yes           |
| unrealized_pnl_query        | Safe       | Yes           |
| unrealized_pnl_static_query | Safe       | Yes           |

---

## Notes

* All operations are read-only
* Live unrealized PnL depends on current market data availability
* Static unrealized PnL does not reflect current market conditions
* Realized PnL should always be derived from stored execution records

```
```
