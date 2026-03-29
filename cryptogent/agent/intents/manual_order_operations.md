````markdown
# MANUAL ORDER OPERATIONS INTENT

## Main Intent
`manual_order_operations`

---

## Description
Handles direct manual order submission, cancellation, reconciliation, and inspection.  
These operations bypass planning and safety layers and are strictly human-only.  
The agent must not execute these actions automatically.

---

## Sub-Intents

### 1. `manual_buy_market`
Submit a manual MARKET BUY order.

### 2. `manual_buy_limit`
Submit a manual LIMIT BUY order.

### 3. `manual_sell_market`
Submit a manual MARKET SELL order.

### 4. `manual_sell_limit`
Submit a manual LIMIT SELL order.

### 5. `manual_order_cancel`
Cancel a manual order.

### 6. `manual_order_reconcile`
Reconcile manual orders with exchange state.

### 7. `manual_order_list`
List manual order history.

### 8. `manual_order_show`
Show a specific manual order.

---

## Internal API Function Mapping

| Sub-Intent              | Function Name               |
|------------------------|-----------------------------|
| manual_buy_market      | manual_buy_market_order     |
| manual_buy_limit       | manual_buy_limit_order      |
| manual_sell_market     | manual_sell_market_order    |
| manual_sell_limit      | manual_sell_limit_order     |
| manual_order_cancel    | cancel_manual_order         |
| manual_order_reconcile | reconcile_manual_orders     |
| manual_order_list      | list_manual_orders          |
| manual_order_show      | get_manual_order            |

---

## Function Specifications

---

### 1. manual_buy_market_order

#### Description
Submits a MARKET BUY order using quote quantity.

#### Function Signature
`manual_buy_market_order(symbol, quote_qty, dry_run=False, confirm=False)`

#### Parameters

| Name      | Type    | Required | Description |
|-----------|---------|----------|------------|
| symbol    | string  | Yes      | Trading pair |
| quote_qty | number  | Yes      | Amount of quote asset to spend |
| dry_run   | boolean | No       | Preview without submitting |
| confirm   | boolean | Yes      | Must be true for execution |

---

### 2. manual_buy_limit_order

#### Description
Submits a LIMIT BUY order.

#### Function Signature
`manual_buy_limit_order(symbol, quote_qty, limit_price, dry_run=False, confirm=False)`

#### Parameters

| Name        | Type    | Required | Description |
|-------------|---------|----------|------------|
| symbol      | string  | Yes      | Trading pair |
| quote_qty   | number  | Yes      | Quote budget |
| limit_price | number  | Yes      | Limit price |
| dry_run     | boolean | No       | Preview only |
| confirm     | boolean | Yes      | Must be true for execution |

---

### 3. manual_sell_market_order

#### Description
Submits a MARKET SELL order.

#### Function Signature
`manual_sell_market_order(symbol, base_qty, dry_run=False, confirm=False)`

#### Parameters

| Name     | Type    | Required | Description |
|----------|---------|----------|------------|
| symbol   | string  | Yes      | Trading pair |
| base_qty | number  | Yes      | Base asset quantity |
| dry_run  | boolean | No       | Preview only |
| confirm  | boolean | Yes      | Must be true for execution |

---

### 4. manual_sell_limit_order

#### Description
Submits a LIMIT SELL order.

#### Function Signature
`manual_sell_limit_order(symbol, base_qty, limit_price, dry_run=False, confirm=False)`

#### Parameters

| Name        | Type    | Required | Description |
|-------------|---------|----------|------------|
| symbol      | string  | Yes      | Trading pair |
| base_qty    | number  | Yes      | Quantity to sell |
| limit_price | number  | Yes      | Limit price |
| dry_run     | boolean | No       | Preview only |
| confirm     | boolean | Yes      | Must be true for execution |

---

### 5. cancel_manual_order

#### Description
Cancels a manual order.

#### Function Signature
`cancel_manual_order(manual_order_id, confirm=False)`

#### Parameters

| Name             | Type    | Required | Description |
|------------------|---------|----------|------------|
| manual_order_id  | integer | Yes      | Manual order identifier |
| confirm          | boolean | Yes      | Must be true for execution |

---

### 6. reconcile_manual_orders

#### Description
Reconciles manual orders with exchange.

#### Function Signature
`reconcile_manual_orders(loop=False, interval_seconds=None, duration_seconds=None)`

#### Parameters

| Name             | Type    | Required | Description |
|------------------|---------|----------|------------|
| loop             | boolean | No       | Continuous reconciliation |
| interval_seconds | integer | No       | Interval between checks |
| duration_seconds | integer | No       | Total runtime |

---

### 7. list_manual_orders

#### Description
Returns manual order history.

#### Function Signature
`list_manual_orders(limit=None)`

---

### 8. get_manual_order

#### Description
Returns details of a manual order.

#### Function Signature
`get_manual_order(manual_order_id)`

---

## Tool Calling Schema

### manual_buy_market

```json
{
  "name": "manual_buy_market_order",
  "arguments": {
    "symbol": "BTCUSDT",
    "quote_qty": 50,
    "dry_run": false,
    "confirm": true
  }
}
````

---

### manual_buy_limit

```json
{
  "name": "manual_buy_limit_order",
  "arguments": {
    "symbol": "BTCUSDT",
    "quote_qty": 50,
    "limit_price": 59000,
    "dry_run": false,
    "confirm": true
  }
}
```

---

### manual_sell_market

```json
{
  "name": "manual_sell_market_order",
  "arguments": {
    "symbol": "BTCUSDT",
    "base_qty": 0.001,
    "confirm": true
  }
}
```

---

### manual_sell_limit

```json
{
  "name": "manual_sell_limit_order",
  "arguments": {
    "symbol": "BTCUSDT",
    "base_qty": 0.001,
    "limit_price": 62000,
    "confirm": true
  }
}
```

---

## Required Parameters Summary

All manual operations:

* `confirm = true` is mandatory
* Required fields must be provided depending on order type

---

## Validation Rules

* Manual operations require explicit confirmation
* Must respect exchange constraints (min notional, lot size)
* Cannot be triggered by automated agent
* Symbol format must be valid
* Quantities must be positive

---

## Intent Routing Rules

* "manual buy market" → `manual_buy_market`
* "manual limit buy" → `manual_buy_limit`
* "manual sell market" → `manual_sell_market`
* "manual sell limit" → `manual_sell_limit`
* "cancel manual order" → `manual_order_cancel`
* "manual orders list" → `manual_order_list`

---

## Safety / Permission

| Sub-Intent         | Risk Level | Agent Allowed |
| ------------------ | ---------- | ------------- |
| all manual actions | Critical   | No            |

---

## Notes

* These operations bypass safety and planning layers
* Must always require human interaction
* Agent should detect but refuse execution
* Only informational access (list/show) may be allowed for agent

```
```
