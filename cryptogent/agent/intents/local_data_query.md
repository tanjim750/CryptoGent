````markdown id="local_data_query_md"
# LOCAL DATA QUERY INTENT

## Main Intent
`local_data_query`

---

## Description
Handles read-only queries on locally stored data in SQLite.  
These operations do not call external APIs and are used for fast access to cached balances, orders, sentiment indices, and audit logs.

---

## Sub-Intents

### 1. `cached_balances_query`
Retrieve cached balances from local database.

### 2. `cached_open_orders_query`
Retrieve cached open orders from local database.

### 3. `cached_fear_greed_query`
Retrieve stored Fear & Greed Index values.

### 4. `audit_log_query`
Retrieve recent audit logs.

---

## Internal API Function Mapping

| Sub-Intent                 | Function Name              |
|---------------------------|----------------------------|
| cached_balances_query     | get_cached_balances        |
| cached_open_orders_query  | get_cached_open_orders     |
| cached_fear_greed_query   | get_cached_fear_greed      |
| audit_log_query           | get_audit_logs             |

---

## Function Specifications

---

### 1. get_cached_balances

#### Description
Returns balances stored in local database.

#### Function Signature
`get_cached_balances(show_all=False, limit=None, filter_text=None)`

#### Parameters

| Name        | Type    | Required | Description |
|-------------|---------|----------|------------|
| show_all    | boolean | No       | Include zero balances |
| limit       | integer | No       | Limit number of results |
| filter_text | string  | No       | Filter by asset substring |

#### Output
```json
{
  "balances": [
    {
      "asset": "BTC",
      "free": "0.01",
      "locked": "0.00"
    }
  ]
}
````

---

### 2. get_cached_open_orders

#### Description

Returns open orders stored in local database.

#### Function Signature

`get_cached_open_orders(symbol=None, limit=None)`

#### Parameters

| Name   | Type   | Required | Description             |
| ------ | ------ | -------- | ----------------------- |
| symbol | string | No       | Filter by trading pair  |
| limit  | int    | No       | Limit number of results |

#### Output

```json id="c8sk2r"
{
  "orders": [
    {
      "symbol": "BTCUSDT",
      "side": "BUY",
      "price": "60000",
      "status": "OPEN",
      "source": "execution"
    }
  ]
}
```

---

### 3. get_cached_fear_greed

#### Description

Returns stored Fear & Greed Index history.

#### Function Signature

`get_cached_fear_greed(limit=None)`

#### Parameters

| Name  | Type | Required | Description              |
| ----- | ---- | -------- | ------------------------ |
| limit | int  | No       | Number of recent entries |

#### Output

```json id="w7gh9k"
{
  "data": [
    {
      "value": 62,
      "classification": "Greed",
      "timestamp": "2026-03-24T10:00:00Z"
    }
  ]
}
```

---

### 4. get_audit_logs

#### Description

Returns recent audit log entries.

#### Function Signature

`get_audit_logs(limit=None)`

#### Parameters

| Name  | Type | Required | Description           |
| ----- | ---- | -------- | --------------------- |
| limit | int  | No       | Number of log entries |

#### Output

```json id="z1h9vp"
{
  "logs": [
    {
      "event": "trade_request_created",
      "timestamp": "2026-03-24T09:00:00Z"
    }
  ]
}
```

---

## Tool Calling Schema

### cached_balances_query

```json id="b1rq8m"
{
  "name": "get_cached_balances",
  "arguments": {
    "show_all": false,
    "limit": "optional integer",
    "filter_text": "optional string"
  }
}
```

---

### cached_open_orders_query

```json id="x3lm9n"
{
  "name": "get_cached_open_orders",
  "arguments": {
    "symbol": "optional string",
    "limit": "optional integer"
  }
}
```

---

### cached_fear_greed_query

```json id="v8p4ks"
{
  "name": "get_cached_fear_greed",
  "arguments": {
    "limit": "optional integer"
  }
}
```

---

### audit_log_query

```json id="q2yt5e"
{
  "name": "get_audit_logs",
  "arguments": {
    "limit": "optional integer"
  }
}
```

---

## Validation Rules

* `symbol` must follow valid trading pair format if provided
* `limit` must be a positive integer
* `filter_text` should be a valid string

---

## Intent Routing Rules

* "show balances", "cached balances" → `cached_balances_query`
* "open orders", "cached orders" → `cached_open_orders_query`
* "fear greed", "sentiment index" → `cached_fear_greed_query`
* "audit logs", "history" → `audit_log_query`

---

## Safety / Permission

| Sub-Intent               | Risk Level | Agent Allowed |
| ------------------------ | ---------- | ------------- |
| cached_balances_query    | Safe       | Yes           |
| cached_open_orders_query | Safe       | Yes           |
| cached_fear_greed_query  | Safe       | Yes           |
| audit_log_query          | Safe       | Yes           |

---

## Notes

* All operations are read-only
* No external API calls are made
* Data reflects last synchronized state

```
```
