````markdown
# RELIABILITY MANAGEMENT INTENT

## Main Intent
`reliability_management`

---

## Description
Handles reconciliation, pause-state inspection, scoped automation resume actions, and reliability event history.  
These operations are used to detect mismatches between local state and exchange state, recover from ambiguity, and manage paused automation scopes safely.

---

## Sub-Intents

### 1. `reliability_status_query`
Retrieve current reliability and automation pause status.

### 2. `reliability_reconcile`
Run reliability reconciliation across balances, orders, positions, and uncertain executions.

### 3. `reliability_resume_global`
Resume globally paused automation.

### 4. `reliability_resume_symbol`
Resume paused automation for a specific symbol.

### 5. `reliability_resume_loop`
Resume paused automation for a specific loop.

### 6. `reliability_events_query`
Retrieve recent reliability and reconciliation event history.

---

## Internal API Function Mapping

| Sub-Intent                | Function Name                 |
|--------------------------|-------------------------------|
| reliability_status_query | get_reliability_status        |
| reliability_reconcile    | run_reliability_reconciliation |
| reliability_resume_global| resume_global_automation      |
| reliability_resume_symbol| resume_symbol_automation      |
| reliability_resume_loop  | resume_loop_automation        |
| reliability_events_query | list_reliability_events       |

---

## Function Specifications

---

### 1. get_reliability_status

#### Description
Returns current automation pause state, last reconciliation status, and last successful synchronization information.

#### Function Signature
`get_reliability_status()`

#### Parameters
None

#### Output
```json
{
  "automation_paused": true,
  "pause_scope": "global",
  "pause_reason": "uncertain_execution_recovery",
  "paused_at_utc": "2026-03-24T09:30:00Z",
  "last_reconciliation_status": "critical_mismatch_detected",
  "last_successful_sync_utc": "2026-03-24T09:20:00Z"
}
````

---

### 2. run_reliability_reconciliation

#### Description

Runs reliability reconciliation across balances, open orders, positions, and uncertain execution state.
This operation may update pause state based on detected ambiguity or mismatches.

#### Function Signature

`run_reliability_reconciliation()`

#### Parameters

None

#### Behavior

* Syncs balances and open orders
* Detects unknown orders, missing orders, balance mismatches, position mismatches, and uncertain execution recovery cases
* Records reconciliation events
* May pause automation globally or by symbol depending on severity

#### Output

```json id="gjc6h4"
{
  "status": "success",
  "reconciliation_result": "symbol_paused",
  "paused_scope": "symbol",
  "symbol": "SOLUSDT",
  "events_recorded": 3
}
```

---

### 3. resume_global_automation

#### Description

Resumes globally paused automation after a healthy reconciliation state.

#### Function Signature

`resume_global_automation(confirm=False)`

#### Parameters

| Name    | Type    | Required | Description                |
| ------- | ------- | -------- | -------------------------- |
| confirm | boolean | No       | Explicit confirmation flag |

#### Output

```json id="4n3xgh"
{
  "status": "resumed",
  "scope": "global"
}
```

---

### 4. resume_symbol_automation

#### Description

Resumes automation for a specific paused symbol.

#### Function Signature

`resume_symbol_automation(symbol, confirm=False)`

#### Parameters

| Name    | Type    | Required | Description                |
| ------- | ------- | -------- | -------------------------- |
| symbol  | string  | Yes      | Trading symbol to resume   |
| confirm | boolean | No       | Explicit confirmation flag |

#### Output

```json id="o4qiu7"
{
  "status": "resumed",
  "scope": "symbol",
  "symbol": "SOLUSDT"
}
```

---

### 5. resume_loop_automation

#### Description

Resumes automation for a specific paused loop.

#### Function Signature

`resume_loop_automation(loop_id, confirm=False)`

#### Parameters

| Name    | Type    | Required | Description                |
| ------- | ------- | -------- | -------------------------- |
| loop_id | integer | Yes      | Loop identifier            |
| confirm | boolean | No       | Explicit confirmation flag |

#### Output

```json id="x68x4s"
{
  "status": "resumed",
  "scope": "loop",
  "loop_id": 12
}
```

---

### 6. list_reliability_events

#### Description

Returns recent reliability and reconciliation event history.

#### Function Signature

`list_reliability_events(limit=None)`

#### Parameters

| Name  | Type    | Required | Description               |
| ----- | ------- | -------- | ------------------------- |
| limit | integer | No       | Maximum number of results |

#### Output

```json id="9f0h7m"
{
  "items": [
    {
      "event_id": 44,
      "event_type": "position_mismatch",
      "severity": "critical",
      "symbol": "SOLUSDT",
      "timestamp": "2026-03-24T09:30:00Z"
    }
  ]
}
```

---

## Tool Calling Schema

### reliability_status_query

```json id="upw42n"
{
  "name": "get_reliability_status",
  "arguments": {}
}
```

---

### reliability_reconcile

```json id="rft9t4"
{
  "name": "run_reliability_reconciliation",
  "arguments": {}
}
```

---

### reliability_resume_global

```json id="jlwmuf"
{
  "name": "resume_global_automation",
  "arguments": {
    "confirm": false
  }
}
```

---

### reliability_resume_symbol

```json id="pu0j2y"
{
  "name": "resume_symbol_automation",
  "arguments": {
    "symbol": "SOLUSDT",
    "confirm": false
  }
}
```

---

### reliability_resume_loop

```json id="1j2w0x"
{
  "name": "resume_loop_automation",
  "arguments": {
    "loop_id": 12,
    "confirm": false
  }
}
```

---

### reliability_events_query

```json id="jlwmdy"
{
  "name": "list_reliability_events",
  "arguments": {
    "limit": "optional integer"
  }
}
```

---

## Required Parameters Summary

### reliability_status_query

No parameters required

### reliability_reconcile

No parameters required

### reliability_resume_global

Optional:

* `confirm`

### reliability_resume_symbol

Required:

* `symbol`

Optional:

* `confirm`

### reliability_resume_loop

Required:

* `loop_id`

Optional:

* `confirm`

### reliability_events_query

Optional:

* `limit`

---

## Validation Rules

* `symbol` must be a valid trading pair format
* `loop_id` must reference an existing paused loop when applicable
* `limit` must be a positive integer if provided
* resume actions should only succeed when the relevant scope is paused and recovery conditions are healthy
* reconciliation results must be persisted as reliability events
* scoped resume must not accidentally resume unrelated paused scopes
* confirmation policy should be enforced for resume actions when required by environment

---

## Intent Routing Rules

* "reliability status", "pause status" → `reliability_status_query`
* "run reliability reconcile", "check mismatches" → `reliability_reconcile`
* "resume automation globally" → `reliability_resume_global`
* "resume symbol SOLUSDT" → `reliability_resume_symbol`
* "resume loop 12" → `reliability_resume_loop`
* "show reliability events" → `reliability_events_query`

---

## Safety / Permission

| Sub-Intent                | Risk Level | Agent Allowed                 |
| ------------------------- | ---------- | ----------------------------- |
| reliability_status_query  | Safe       | Yes                           |
| reliability_reconcile     | Medium     | Yes                           |
| reliability_resume_global | High       | Yes, with confirmation policy |
| reliability_resume_symbol | High       | Yes, with confirmation policy |
| reliability_resume_loop   | High       | Yes, with confirmation policy |
| reliability_events_query  | Safe       | Yes                           |

---

## Notes

* Reconciliation may change automation pause state based on detected ambiguity
* Resume actions should be guarded by confirmation and health checks
* Reliability scope management should remain explicit: global, symbol, and loop scopes must be handled separately
* These operations are safety-critical for automated trading continuity

```
```
