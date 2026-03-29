````markdown
# POSITION MANAGEMENT INTENT

## Main Intent
`position_management`

---

## Description
Handles position listing, position detail retrieval, and live position review.  
These operations are read-focused and do not place or cancel exchange orders. They are used to inspect stored positions and, when requested, compute live unrealized state using current market data.

---

## Sub-Intents

### 1. `position_list_query`
List stored positions.

### 2. `position_show`
Retrieve details of a specific position.

### 3. `position_live_review`
Retrieve a position with live price context and review its current state.

---

## Internal API Function Mapping

| Sub-Intent           | Function Name        |
|---------------------|----------------------|
| position_list_query | list_positions       |
| position_show       | get_position         |
| position_live_review| review_live_position |

---

## Function Specifications

---

### 1. list_positions

#### Description
Returns stored positions, including reserved or locked quantity where applicable.

#### Function Signature
`list_positions(limit=None)`

#### Parameters

| Name  | Type    | Required | Description |
|-------|---------|----------|------------|
| limit | integer | No       | Maximum number of results |

#### Output
```json
{
  "items": [
    {
      "position_id": 9,
      "symbol": "BTCUSDT",
      "status": "OPEN",
      "quantity": "0.0012",
      "locked_qty": "0.0004",
      "entry_price": "62000"
    }
  ]
}
````

---

### 2. get_position

#### Description

Returns details of a specific stored position.
If `live=true`, current market price is fetched and unrealized PnL is computed.

#### Function Signature

`get_position(position_id, live=False)`

#### Parameters

| Name        | Type    | Required | Description                                           |
| ----------- | ------- | -------- | ----------------------------------------------------- |
| position_id | integer | Yes      | Position identifier                                   |
| live        | boolean | No       | Fetch live price and compute current unrealized state |

#### Output

```json id="nsv3qc"
{
  "position_id": 9,
  "symbol": "BTCUSDT",
  "status": "OPEN",
  "quantity": "0.0012",
  "locked_qty": "0.0004",
  "entry_price": "62000",
  "live_price": "62850",
  "unrealized_pnl_quote": "1.02"
}
```

---

### 3. review_live_position

#### Description

Performs a live review of a stored position using current market data and returns a structured position assessment.

#### Function Signature

`review_live_position(position_id)`

#### Parameters

| Name        | Type    | Required | Description         |
| ----------- | ------- | -------- | ------------------- |
| position_id | integer | Yes      | Position identifier |

#### Behavior

* Loads stored position
* Fetches live price from the position's market data environment
* Computes unrealized PnL
* Returns a structured live review summary

#### Output

```json id="8xgi0a"
{
  "position_id": 9,
  "symbol": "BTCUSDT",
  "status": "OPEN",
  "entry_price": "62000",
  "live_price": "62850",
  "quantity": "0.0012",
  "unrealized_pnl_quote": "1.02",
  "review": "position_in_profit"
}
```

---

## Tool Calling Schema

### position_list_query

```json id="6c8h0r"
{
  "name": "list_positions",
  "arguments": {
    "limit": "optional integer"
  }
}
```

---

### position_show

```json id="1du3xr"
{
  "name": "get_position",
  "arguments": {
    "position_id": 9,
    "live": false
  }
}
```

---

### position_live_review

```json id="x1a91a"
{
  "name": "review_live_position",
  "arguments": {
    "position_id": 9
  }
}
```

---

## Required Parameters Summary

### position_list_query

Optional:

* `limit`

### position_show

Required:

* `position_id`

Optional:

* `live`

### position_live_review

Required:

* `position_id`

---

## Validation Rules

* `position_id` must reference an existing stored position
* `limit` must be a positive integer if provided
* live review requires market data access for the position's configured market environment
* position queries must not mutate stored state except for optional computed response fields

---

## Intent Routing Rules

* "list positions", "show positions" → `position_list_query`
* "show position 9" → `position_show`
* "review position 9", "live position review" → `position_live_review`

---

## Safety / Permission

| Sub-Intent           | Risk Level | Agent Allowed |
| -------------------- | ---------- | ------------- |
| position_list_query  | Safe       | Yes           |
| position_show        | Safe       | Yes           |
| position_live_review | Safe       | Yes           |

---

## Notes

* These operations do not place, cancel, or modify exchange orders
* Live review depends on current market data availability
* Stored position state and computed live response should remain clearly separated

```
```
