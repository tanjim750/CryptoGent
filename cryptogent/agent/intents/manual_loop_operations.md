````markdown
# MANUAL LOOP OPERATIONS INTENT

## Main Intent
`manual_loop_operations`

---

## Description
Handles manual loop trading preset creation, loop session start, reconciliation, inspection, and stop actions.  
These operations bypass planning and safety layers and are strictly human-only for any action that can create, submit, cancel, advance, or stop exchange-facing loop activity.  
The agent must not execute these actions automatically.

---

## Sub-Intents

### 1. `manual_loop_preset_create`
Create a reusable manual loop preset.

### 2. `manual_loop_start`
Start a manual loop session from a preset or direct runtime configuration.

### 3. `manual_loop_status_query`
Retrieve current status of a manual loop session.

### 4. `manual_loop_list`
List stored manual loop sessions.

### 5. `manual_loop_preset_list`
List stored manual loop presets.

### 6. `manual_loop_preset_show`
Retrieve details of a specific manual loop preset.

### 7. `manual_loop_reconcile`
Reconcile manual loop state and advance loop legs when conditions are met.

### 8. `manual_loop_stop`
Stop a running manual loop session.

---

## Internal API Function Mapping

| Sub-Intent               | Function Name             |
|-------------------------|---------------------------|
| manual_loop_preset_create | create_manual_loop_preset |
| manual_loop_start       | start_manual_loop         |
| manual_loop_status_query | get_manual_loop_status    |
| manual_loop_list        | list_manual_loops         |
| manual_loop_preset_list | list_manual_loop_presets  |
| manual_loop_preset_show | get_manual_loop_preset    |
| manual_loop_reconcile   | reconcile_manual_loops    |
| manual_loop_stop        | stop_manual_loop          |

---

## Function Specifications

---

### 1. create_manual_loop_preset

#### Description
Creates and stores a reusable manual loop preset.  
This operation does not submit any exchange order.

#### Function Signature
`create_manual_loop_preset(loop_config, confirm=False)`

#### Parameters

| Name        | Type    | Required | Description |
|-------------|---------|----------|------------|
| loop_config | object  | Yes      | Loop preset configuration |
| confirm     | boolean | Yes      | Must be true for execution |

#### Loop Config Fields

| Name               | Type    | Required | Description |
|--------------------|---------|----------|------------|
| symbol             | string  | Yes      | Trading pair |
| quote_qty          | number  | Yes      | Quote-side budget for entry |
| entry_type         | string  | Yes      | `BUY_MARKET` or `BUY_LIMIT` |
| entry_limit_price  | number  | No       | Required when entry type is `BUY_LIMIT` |
| take_profit_pct    | number  | No       | Percent take-profit rule |
| take_profit_abs    | number  | No       | Absolute quote take-profit rule |
| rebuy_pct          | number  | No       | Percent rebuy offset |
| rebuy_abs          | number  | No       | Absolute rebuy offset |
| stop_loss_pct      | number  | No       | Percent stop-loss threshold |
| stop_loss_abs      | number  | No       | Absolute quote stop-loss threshold |
| stop_loss_action   | string  | No       | `stop_only` or `stop_and_exit` |
| cleanup_policy     | string  | No       | `cancel-open`, `none`, or `cancel-open-and-exit` |

#### Output
```json
{
  "preset_id": 12,
  "status": "CREATED",
  "symbol": "SOLUSDT",
  "entry_type": "BUY_MARKET"
}
````

---

### 2. start_manual_loop

#### Description

Starts a manual loop session using either a preset identifier or direct runtime configuration.
This operation may submit exchange orders and must be treated as human-only.

#### Function Signature

`start_manual_loop(loop_config_or_preset_id, max_cycles, confirm=False, dry_run=False)`

#### Parameters

| Name                     | Type           | Required | Description                                                        |
| ------------------------ | -------------- | -------- | ------------------------------------------------------------------ |
| loop_config_or_preset_id | object/integer | Yes      | Preset ID or inline loop configuration                             |
| max_cycles               | integer        | Yes      | Number of loop cycles, `0` may indicate infinite loop if supported |
| confirm                  | boolean        | Yes      | Must be true for execution                                         |
| dry_run                  | boolean        | No       | Preview only without submitting                                    |

#### Output

```json id="sgro7r"
{
  "loop_id": 31,
  "status": "RUNNING",
  "symbol": "SOLUSDT",
  "max_cycles": 3
}
```

---

### 3. get_manual_loop_status

#### Description

Returns the current status of a manual loop session.

#### Function Signature

`get_manual_loop_status(loop_id=None)`

#### Parameters

| Name    | Type    | Required | Description                    |
| ------- | ------- | -------- | ------------------------------ |
| loop_id | integer | No       | Manual loop session identifier |

#### Output

```json id="4gfdgc"
{
  "loop_id": 31,
  "status": "RUNNING",
  "symbol": "SOLUSDT",
  "current_cycle": 1,
  "max_cycles": 3
}
```

---

### 4. list_manual_loops

#### Description

Lists stored manual loop sessions.

#### Function Signature

`list_manual_loops(limit=None)`

#### Parameters

| Name  | Type    | Required | Description               |
| ----- | ------- | -------- | ------------------------- |
| limit | integer | No       | Maximum number of results |

#### Output

```json id="mgepp2"
{
  "items": [
    {
      "loop_id": 31,
      "symbol": "SOLUSDT",
      "status": "RUNNING"
    }
  ]
}
```

---

### 5. list_manual_loop_presets

#### Description

Lists stored manual loop presets.

#### Function Signature

`list_manual_loop_presets(limit=None)`

#### Parameters

| Name  | Type    | Required | Description               |
| ----- | ------- | -------- | ------------------------- |
| limit | integer | No       | Maximum number of results |

#### Output

```json id="xuk1y9"
{
  "items": [
    {
      "preset_id": 12,
      "symbol": "SOLUSDT",
      "entry_type": "BUY_MARKET"
    }
  ]
}
```

---

### 6. get_manual_loop_preset

#### Description

Returns details of a specific manual loop preset.

#### Function Signature

`get_manual_loop_preset(preset_id)`

#### Parameters

| Name      | Type    | Required | Description                   |
| --------- | ------- | -------- | ----------------------------- |
| preset_id | integer | Yes      | Manual loop preset identifier |

#### Output

```json id="5wtih6"
{
  "preset_id": 12,
  "symbol": "SOLUSDT",
  "quote_qty": 1000,
  "entry_type": "BUY_MARKET",
  "take_profit_pct": 1.0,
  "rebuy_pct": -1.0
}
```

---

### 7. reconcile_manual_loops

#### Description

Reconciles manual loop state with exchange data and advances loop legs only after full fills.
This operation may submit or cancel exchange orders depending on loop state.

#### Function Signature

`reconcile_manual_loops(loop_id=None, loop=False, interval_seconds=None, duration_seconds=None, confirm=False)`

#### Parameters

| Name             | Type    | Required | Description                    |
| ---------------- | ------- | -------- | ------------------------------ |
| loop_id          | integer | No       | Manual loop session identifier |
| loop             | boolean | No       | Repeated reconciliation mode   |
| interval_seconds | integer | No       | Loop interval in seconds       |
| duration_seconds | integer | No       | Total runtime for loop mode    |
| confirm          | boolean | Yes      | Must be true for execution     |

#### Output

```json id="fgd77v"
{
  "status": "success",
  "reconciled_loops": 1,
  "advanced_legs": 1
}
```

---

### 8. stop_manual_loop

#### Description

Stops a running manual loop and applies the configured cleanup policy.

#### Function Signature

`stop_manual_loop(loop_id=None, confirm=False)`

#### Parameters

| Name    | Type    | Required | Description                    |
| ------- | ------- | -------- | ------------------------------ |
| loop_id | integer | No       | Manual loop session identifier |
| confirm | boolean | Yes      | Must be true for execution     |

#### Output

```json id="igpxp2"
{
  "loop_id": 31,
  "status": "STOPPED"
}
```

---

## Tool Calling Schema

### manual_loop_preset_create

```json id="ewi2h4"
{
  "name": "create_manual_loop_preset",
  "arguments": {
    "loop_config": {
      "symbol": "SOLUSDT",
      "quote_qty": 1000,
      "entry_type": "BUY_MARKET",
      "take_profit_pct": 1.0,
      "rebuy_pct": -1.0,
      "stop_loss_action": "stop_only",
      "cleanup_policy": "cancel-open"
    },
    "confirm": true
  }
}
```

---

### manual_loop_start

```json id="7l87j1"
{
  "name": "start_manual_loop",
  "arguments": {
    "loop_config_or_preset_id": 12,
    "max_cycles": 3,
    "confirm": true,
    "dry_run": false
  }
}
```

---

### manual_loop_status_query

```json id="gvdmoq"
{
  "name": "get_manual_loop_status",
  "arguments": {
    "loop_id": 31
  }
}
```

---

### manual_loop_list

```json id="5j74pj"
{
  "name": "list_manual_loops",
  "arguments": {
    "limit": "optional integer"
  }
}
```

---

### manual_loop_preset_list

```json id="t5alcb"
{
  "name": "list_manual_loop_presets",
  "arguments": {
    "limit": "optional integer"
  }
}
```

---

### manual_loop_preset_show

```json id="k1lxef"
{
  "name": "get_manual_loop_preset",
  "arguments": {
    "preset_id": 12
  }
}
```

---

### manual_loop_reconcile

```json id="olke6v"
{
  "name": "reconcile_manual_loops",
  "arguments": {
    "loop_id": 31,
    "loop": false,
    "interval_seconds": "optional integer",
    "duration_seconds": "optional integer",
    "confirm": true
  }
}
```

---

### manual_loop_stop

```json id="f9xz4l"
{
  "name": "stop_manual_loop",
  "arguments": {
    "loop_id": 31,
    "confirm": true
  }
}
```

---

## Required Parameters Summary

### manual_loop_preset_create

Required:

* `loop_config`
* `confirm`

Conditionally required inside `loop_config`:

* `entry_limit_price` when `entry_type = "BUY_LIMIT"`

Optional inside `loop_config`:

* `take_profit_pct`
* `take_profit_abs`
* `rebuy_pct`
* `rebuy_abs`
* `stop_loss_pct`
* `stop_loss_abs`
* `stop_loss_action`
* `cleanup_policy`

### manual_loop_start

Required:

* `loop_config_or_preset_id`
* `max_cycles`
* `confirm`

Optional:

* `dry_run`

### manual_loop_status_query

Optional:

* `loop_id`

### manual_loop_list

Optional:

* `limit`

### manual_loop_preset_list

Optional:

* `limit`

### manual_loop_preset_show

Required:

* `preset_id`

### manual_loop_reconcile

Required:

* `confirm`

Optional:

* `loop_id`
* `loop`
* `interval_seconds`
* `duration_seconds`

### manual_loop_stop

Required:

* `confirm`

Optional:

* `loop_id`

---

## Validation Rules

* `symbol` must be a valid trading pair format
* `quote_qty` must be greater than zero
* `entry_type` must be one of:

  * `BUY_MARKET`
  * `BUY_LIMIT`
* `entry_limit_price` is required for `BUY_LIMIT`
* at least one take-profit rule should be provided if loop logic requires it
* rebuy configuration should follow supported percent or absolute format
* `stop_loss_action` must be one of:

  * `stop_only`
  * `stop_and_exit`
* `cleanup_policy` must be one of:

  * `cancel-open`
  * `none`
  * `cancel-open-and-exit`
* `max_cycles` must be zero or a positive integer
* `preset_id` must reference an existing preset
* `loop_id` must reference an existing loop session when provided
* all exchange-facing loop actions require explicit confirmation
* manual loop actions must not be triggered by automated agent behavior

---

## Intent Routing Rules

* "create loop preset" → `manual_loop_preset_create`
* "start manual loop" → `manual_loop_start`
* "loop status" → `manual_loop_status_query`
* "list loops" → `manual_loop_list`
* "list loop presets" → `manual_loop_preset_list`
* "show loop preset 12" → `manual_loop_preset_show`
* "reconcile loop" → `manual_loop_reconcile`
* "stop loop" → `manual_loop_stop`

---

## Safety / Permission

| Sub-Intent                | Risk Level | Agent Allowed |
| ------------------------- | ---------- | ------------- |
| manual_loop_preset_create | Critical   | No            |
| manual_loop_start         | Critical   | No            |
| manual_loop_status_query  | Safe       | Yes           |
| manual_loop_list          | Safe       | Yes           |
| manual_loop_preset_list   | Safe       | Yes           |
| manual_loop_preset_show   | Safe       | Yes           |
| manual_loop_reconcile     | Critical   | No            |
| manual_loop_stop          | Critical   | No            |

---

## Notes

* These operations bypass normal planning and safety layers
* Any action that can create, submit, advance, cancel, or stop loop-driven exchange activity is human-only
* Agent should detect these intents and refuse execution for restricted actions
* Read-only inspection of loop presets and loop status may be exposed to the agent

```
```
