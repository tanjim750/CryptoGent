````markdown id="sync_operations_md"
# SYNC OPERATIONS INTENT

## Main Intent
`sync_operations`

---

## Description
Handles synchronization of external exchange data into the local SQLite database.  
These operations fetch live data from external sources (Binance, Fear & Greed Index) and persist it locally for consistent state management.

---

## Sub-Intents

### 1. `sync_startup`
Perform full startup synchronization (account snapshot, balances, open orders).

### 2. `sync_balances`
Synchronize balances from exchange to local database.

### 3. `sync_open_orders`
Synchronize open orders from exchange to local database.

### 4. `sync_fear_greed`
Fetch and store Fear & Greed Index data.

---

## Internal API Function Mapping

| Sub-Intent        | Function Name                     |
|------------------|----------------------------------|
| sync_startup     | run_startup_sync                 |
| sync_balances    | sync_balances_to_local_store     |
| sync_open_orders | sync_open_orders_to_local_store  |
| sync_fear_greed  | sync_fear_greed_index            |

---

## Function Specifications

---

### 1. run_startup_sync

#### Description
Performs a full synchronization including account snapshot, balances, and open orders.

#### Function Signature
`run_startup_sync()`

#### Parameters
None

#### Behavior
- Fetch account data from exchange
- Sync balances
- Sync open orders
- Store all data into SQLite

#### Output
```json
{
  "status": "success",
  "balances_synced": true,
  "orders_synced": true
}
````

---

### 2. sync_balances_to_local_store

#### Description

Fetches balances from the exchange and stores them locally.

#### Function Signature

`sync_balances_to_local_store()`

#### Parameters

None

#### Behavior

* Calls exchange account endpoint
* Updates local balances table

#### Output

```json id="j2h8sa"
{
  "status": "success",
  "updated_records": 5
}
```

---

### 3. sync_open_orders_to_local_store

#### Description

Fetches open orders and stores them locally.

#### Function Signature

`sync_open_orders_to_local_store(symbol=None)`

#### Parameters

| Name   | Type   | Required | Description                      |
| ------ | ------ | -------- | -------------------------------- |
| symbol | string | No       | Filter by symbol (e.g., BTCUSDT) |

#### Behavior

* Fetch open orders from exchange
* Store/update local records

#### Output

```json id="9e7x4k"
{
  "status": "success",
  "orders_synced": 3
}
```

---

### 4. sync_fear_greed_index

#### Description

Fetches the latest Fear & Greed Index and stores it locally.

#### Function Signature

`sync_fear_greed_index()`

#### Parameters

None

#### Behavior

* Fetch data from external API (Alternative.me)
* Store latest value into SQLite

#### Output

```json id="m0yq6w"
{
  "status": "success",
  "value": 62,
  "classification": "Greed"
}
```

---

## Tool Calling Schema

### sync_startup

```json id="p7z4ru"
{
  "name": "run_startup_sync",
  "arguments": {}
}
```

---

### sync_balances

```json id="o1d4xy"
{
  "name": "sync_balances_to_local_store",
  "arguments": {}
}
```

---

### sync_open_orders

```json id="2yq8sl"
{
  "name": "sync_open_orders_to_local_store",
  "arguments": {
    "symbol": "optional string"
  }
}
```

---

### sync_fear_greed

```json id="l5mvqz"
{
  "name": "sync_fear_greed_index",
  "arguments": {}
}
```

---

## Validation Rules

* Exchange API credentials must be configured for balance/order sync
* Symbol (if provided) must follow valid trading pair format
* External API must be reachable for Fear & Greed sync

---

## Intent Routing Rules

* "startup sync", "initialize sync" → `sync_startup`
* "sync balances" → `sync_balances`
* "sync open orders" → `sync_open_orders`
* "fear greed sync", "update fear index" → `sync_fear_greed`

---

## Safety / Permission

| Sub-Intent       | Risk Level | Agent Allowed |
| ---------------- | ---------- | ------------- |
| sync_startup     | Medium     | Yes           |
| sync_balances    | Medium     | Yes           |
| sync_open_orders | Medium     | Yes           |
| sync_fear_greed  | Safe       | Yes           |

---

## Notes

* No trading actions are performed
* Data is persisted locally in SQLite
* These operations ensure consistency between exchange and local state

```
```
