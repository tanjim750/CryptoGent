````markdown
# ORDER MANAGEMENT INTENT

## Main Intent
`order_management`

---

## Description
Handles cancellation of existing open orders tracked in the local system.  
These operations interact with the exchange to cancel orders and update local state accordingly.  
Only non-MARKET orders created by the system (manual or execution) are eligible for cancellation.

---

## Sub-Intents

### 1. `order_cancel`
Cancel an open order by order identifier.

---

## Internal API Function Mapping

| Sub-Intent   | Function Name       |
|--------------|---------------------|
| order_cancel | cancel_open_order   |

---

## Function Specifications

---

### 1. cancel_open_order

#### Description
Cancels a cached open order on the exchange and updates local records.

#### Function Signature
`cancel_open_order(order_id, confirm=False)`

#### Parameters

| Name      | Type    | Required | Description |
|-----------|---------|----------|------------|
| order_id  | integer | Yes      | Exchange order identifier |
| confirm   | boolean | No       | Explicit confirmation flag |

#### Behavior
- Validates order exists in local cache
- Ensures order is cancellable
- Sends cancel request to exchange
- Updates local order state
- Refreshes cached balances and open orders
- Recomputes locked quantities for positions

#### Output
```json
{
  "order_id": 123456,
  "status": "CANCELLED",
  "symbol": "BTCUSDT"
}
````

---

## Tool Calling Schema

### order_cancel

```json
{
  "name": "cancel_open_order",
  "arguments": {
    "order_id": 123456,
    "confirm": false
  }
}
```

---

## Required Parameters Summary

### order_cancel

Required:

* `order_id`

Optional:

* `confirm`

---

## Validation Rules

* `order_id` must reference an existing cached open order
* only non-MARKET orders can be cancelled
* only orders created by system (`manual` or `execution`) are cancellable
* external orders must not be cancelled
* order must be in an open state
* confirmation policy should be enforced if required by environment

---

## Intent Routing Rules

* "cancel order 123456" → `order_cancel`
* "cancel open order" → `order_cancel`

---

## Safety / Permission

| Sub-Intent   | Risk Level | Agent Allowed                 |
| ------------ | ---------- | ----------------------------- |
| order_cancel | High       | Yes, with confirmation policy |

---

## Notes

* This operation affects real exchange state
* Should always verify order ownership and source before cancellation
* Local state must remain consistent with exchange after cancellation

```
```
