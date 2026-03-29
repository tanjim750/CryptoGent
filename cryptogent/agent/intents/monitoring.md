````markdown
# MONITORING INTENT

## Main Intent
`monitoring`

---

## Description
Handles position monitoring operations including one-time monitoring checks, repeated monitoring loops, and monitoring event history retrieval.  
These operations do not execute trades. They evaluate open positions using live market data and persist monitoring decisions such as hold, exit recommendation, reevaluation, or data unavailable.

---

## Sub-Intents

### 1. `monitor_once`
Run one monitoring tick for one position or all relevant positions.

### 2. `monitor_loop`
Run repeated monitoring ticks for one position or all relevant positions.

### 3. `monitor_events_query`
Retrieve stored monitoring event history.

---

## Internal API Function Mapping

| Sub-Intent           | Function Name        |
|---------------------|----------------------|
| monitor_once        | run_monitoring_tick  |
| monitor_loop        | run_monitoring_loop  |
| monitor_events_query| list_monitoring_events |

---

## Function Specifications

---

### 1. run_monitoring_tick

#### Description
Runs a single monitoring cycle using live market data and stores a monitoring event.

#### Function Signature
`run_monitoring_tick(position_id=None, verbose=False)`

#### Parameters

| Name        | Type    | Required | Description |
|-------------|---------|----------|------------|
| position_id | integer | No       | Specific position identifier |
| verbose     | boolean | No       | Include additional debugging or decision detail |

#### Behavior
- Fetches current price for the targeted position(s)
- Computes unrealized PnL
- Evaluates monitoring logic
- Persists a monitoring event
- Returns a decision summary

#### Output
```json
{
  "status": "success",
  "position_id": 9,
  "decision": "hold",
  "reason_code": "within_expected_range",
  "unrealized_pnl_quote": "1.02"
}
````

---

### 2. run_monitoring_loop

#### Description

Runs repeated monitoring ticks using configured or provided interval values.

#### Function Signature

`run_monitoring_loop(interval_seconds=None, duration_seconds=None, position_id=None, verbose=False)`

#### Parameters

| Name             | Type    | Required | Description                                     |
| ---------------- | ------- | -------- | ----------------------------------------------- |
| interval_seconds | integer | No       | Monitoring interval in seconds                  |
| duration_seconds | integer | No       | Total monitoring duration in seconds            |
| position_id      | integer | No       | Specific position identifier                    |
| verbose          | boolean | No       | Include additional debugging or decision detail |

#### Behavior

* Runs repeated monitoring ticks
* Applies configured or default interval when not provided
* Applies monitoring backoff on repeated fetch failures
* Persists monitoring events for each tick

#### Output

```json id="g5e0qi"
{
  "status": "success",
  "ticks_run": 5,
  "position_id": 9,
  "last_decision": "reevaluate"
}
```

---

### 3. list_monitoring_events

#### Description

Returns stored monitoring event history.

#### Function Signature

`list_monitoring_events(limit=None)`

#### Parameters

| Name  | Type    | Required | Description               |
| ----- | ------- | -------- | ------------------------- |
| limit | integer | No       | Maximum number of results |

#### Output

```json id="hxhjlwm"
{
  "items": [
    {
      "event_id": 101,
      "position_id": 9,
      "decision": "hold",
      "reason_code": "within_expected_range",
      "timestamp": "2026-03-24T10:15:00Z"
    }
  ]
}
```

---

## Tool Calling Schema

### monitor_once

```json id="2r76ka"
{
  "name": "run_monitoring_tick",
  "arguments": {
    "position_id": "optional integer",
    "verbose": false
  }
}
```

---

### monitor_loop

```json id="m2cz95"
{
  "name": "run_monitoring_loop",
  "arguments": {
    "interval_seconds": "optional integer",
    "duration_seconds": "optional integer",
    "position_id": "optional integer",
    "verbose": false
  }
}
```

---

### monitor_events_query

```json id="g7a5h7"
{
  "name": "list_monitoring_events",
  "arguments": {
    "limit": "optional integer"
  }
}
```

---

## Required Parameters Summary

### monitor_once

Optional:

* `position_id`
* `verbose`

### monitor_loop

Optional:

* `interval_seconds`
* `duration_seconds`
* `position_id`
* `verbose`

### monitor_events_query

Optional:

* `limit`

---

## Validation Rules

* `position_id` must reference an existing stored position when provided
* `interval_seconds` must be a positive integer if provided
* `duration_seconds` must be a positive integer if provided
* `limit` must be a positive integer if provided
* monitoring decisions must be one of:

  * `hold`
  * `exit_recommended`
  * `reevaluate`
  * `data_unavailable`
* monitoring must not place or cancel exchange orders

---

## Intent Routing Rules

* "monitor once", "run one monitoring check" → `monitor_once`
* "start monitoring loop", "monitor repeatedly" → `monitor_loop`
* "show monitoring events", "monitor history" → `monitor_events_query`

---

## Safety / Permission

| Sub-Intent           | Risk Level | Agent Allowed |
| -------------------- | ---------- | ------------- |
| monitor_once         | Safe       | Yes           |
| monitor_loop         | Low        | Yes           |
| monitor_events_query | Safe       | Yes           |

---

## Notes

* Monitoring produces decisions only and does not execute trades
* Live market data availability affects monitoring quality
* Backoff behavior should be handled internally on repeated data fetch failures
* Monitoring events should be persisted for later review and audit

```
```
