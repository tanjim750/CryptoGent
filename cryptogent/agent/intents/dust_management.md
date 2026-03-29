````markdown
# DUST MANAGEMENT INTENT

## Main Intent
`dust_management`

---

## Description
Handles read-only inspection of the dust ledger.  
These operations are accounting-focused and do not place, cancel, or auto-trade any asset. They are used to inspect small residual balances tracked by the system.

---

## Sub-Intents

### 1. `dust_list_query`
List dust ledger entries.

### 2. `dust_show`
Retrieve details for a specific dust asset entry.

---

## Internal API Function Mapping

| Sub-Intent      | Function Name    |
|----------------|------------------|
| dust_list_query| list_dust_ledger |
| dust_show      | get_dust_ledger  |

---

## Function Specifications

---

### 1. list_dust_ledger

#### Description
Returns dust ledger rows for tracked assets, including effective dust values when available.

#### Function Signature
`list_dust_ledger(limit=None)`

#### Parameters

| Name  | Type    | Required | Description |
|-------|---------|----------|------------|
| limit | integer | No       | Maximum number of results |

#### Output
```json
{
  "items": [
    {
      "asset": "BTC",
      "dust_balance": "0.00000031",
      "effective_dust": "0.00000020",
      "cached_free_balance": "0.00000050"
    }
  ]
}
````

---

### 2. get_dust_ledger

#### Description

Returns a single dust ledger entry for a specific asset, including cached free balance and effective dust if available.

#### Function Signature

`get_dust_ledger(asset)`

#### Parameters

| Name  | Type   | Required | Description  |
| ----- | ------ | -------- | ------------ |
| asset | string | Yes      | Asset symbol |

#### Output

```json id="n7u9k2"
{
  "asset": "BTC",
  "dust_balance": "0.00000031",
  "effective_dust": "0.00000020",
  "cached_free_balance": "0.00000050",
  "notes": []
}
```

---

## Tool Calling Schema

### dust_list_query

```json id="e4v8w1"
{
  "name": "list_dust_ledger",
  "arguments": {
    "limit": "optional integer"
  }
}
```

---

### dust_show

```json id="m2r7q4"
{
  "name": "get_dust_ledger",
  "arguments": {
    "asset": "BTC"
  }
}
```

---

## Required Parameters Summary

### dust_list_query

Optional:

* `limit`

### dust_show

Required:

* `asset`

---

## Validation Rules

* `asset` must be a valid asset symbol
* `limit` must be a positive integer if provided
* dust ledger queries must remain read-only
* effective dust calculation should not exceed cached free balance constraints when such logic is applied

---

## Intent Routing Rules

* "list dust", "show dust ledger" → `dust_list_query`
* "show BTC dust", "dust for BTC" → `dust_show`

---

## Safety / Permission

| Sub-Intent      | Risk Level | Agent Allowed |
| --------------- | ---------- | ------------- |
| dust_list_query | Safe       | Yes           |
| dust_show       | Safe       | Yes           |

---

## Notes

* These operations are accounting-only
* No automatic trading or sweeping should be triggered
* Dust ledger values should be treated separately from tradable balance logic

```
```
