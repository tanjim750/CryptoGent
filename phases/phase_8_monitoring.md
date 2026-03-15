````markdown
# Phase 8 – Monitoring

This phase introduces the **continuous post-execution control loop** of CryptoGent.

By this stage, the system should already be able to:

- create a validated trade request
- build a trade plan
- pass deterministic validation and risk checks
- execute a Spot order
- create and persist an active position
- synchronize account state after execution

Phase 8 is responsible for **tracking active positions and deciding when re-evaluation or exit logic should be triggered**.

This phase should not yet focus on external reconciliation reliability concerns beyond what is necessary for monitoring.  
Its main purpose is to watch the trade lifecycle after entry.

---

# Phase Scope

This phase implements the following steps from the implementation roadmap:

30. monitoring loop  
31. exit control  
32. re-evaluation triggers  

---

# Core Objective

After completing Phase 8, CryptoGent should be able to:

- continuously monitor active positions
- check price movement and PnL progression
- detect target profit conditions
- detect stop-loss conditions
- detect deadline conditions
- trigger trade re-evaluation when meaningful changes occur
- trigger an exit decision when required

This phase should prepare the system for safe automated trade closure.

---

# Layers Covered in This Phase

This phase activates the following layers:

17. Deadline and Exit Control Layer  
18. Monitoring and Re-evaluation Layer  

Supporting layers involved:

4. Exchange Connection Layer  
5. Account State Synchronization Layer  
6. Local State, Persistence, and Recovery Layer  
7. Market Data Layer  
16. Position Management Layer  
20. Audit, Logging, and Reporting Layer  

---

# Monitoring Philosophy

CryptoGent must not assume that a trade can be left unattended after execution.

Once a position is open, the system should keep track of:

- current price
- unrealized PnL
- stop-loss proximity
- target progress
- deadline pressure
- position status

The monitoring loop should remain **deterministic and event-driven where possible**.

The system should avoid unnecessary heavy computation or continuous LLM usage.

---

# Monitoring Loop

The monitoring loop is the heart of this phase.

It should periodically inspect the active position and relevant market data.

Suggested MVP behavior:

- run at a configured interval
- inspect only active positions
- load current position state from local DB
- refresh relevant market data
- evaluate exit and re-evaluation conditions
- persist monitoring state

---

# Monitoring Interval

The interval should come from configuration.

Example:

```yaml
trading:
  monitoring_interval: 60
````

Meaning:

```text
every 60 seconds
```

This interval should be easy to change.

For MVP, the loop can be implemented as a simple scheduler or repeating task inside the local runtime.

---

# Monitoring Inputs

Inputs include:

* active position
* latest market price
* latest candle context if needed
* current timestamp
* target profit percent
* stop-loss percent
* deadline
* position entry price
* execution metadata

---

# Position State Required

The monitoring logic depends on position data such as:

* symbol
* side
* entry price
* quantity
* target profit
* stop-loss
* deadline
* current status
* opened_at

Only open positions should be actively monitored.

---

# Price Tracking

The loop must retrieve current price for the active symbol.

Recommended endpoint:

```text
GET /api/v3/ticker/price
```

For richer context, it may also fetch:

* 24hr stats
* a small recent candle window

But current price is the minimum requirement for MVP exit logic.

---

# Profit and Loss Tracking

The monitoring phase should calculate at least the unrealized PnL.

Suggested outputs:

* current notional value
* price change percent from entry
* unrealized profit/loss
* target distance
* stop-loss distance

Example concept:

```text
price_change_percent = ((current_price - entry_price) / entry_price) * 100
```

This calculation should be deterministic and reusable.

---

# Exit Control

Exit control determines when the system should stop holding the position and prepare an exit order.

This phase should not directly manage reconciliation concerns outside monitoring, but it must produce a clean and deterministic exit trigger.

---

# Exit Conditions

At minimum, the system must support the following exit conditions.

## Target Profit Reached

If the position reaches or exceeds the target profit threshold:

* trigger exit

---

## Stop-Loss Reached

If the position reaches or crosses the stop-loss threshold:

* trigger exit

This is mandatory.

---

## Deadline Reached

If the configured deadline has passed:

* trigger exit

The system must not keep the trade open indefinitely once the deadline expires.

---

## Strategy Invalidation Trigger

The MVP may support a simple invalidation rule, such as:

* strong adverse move before target
* repeated weakness confirmed by basic monitoring logic

This can remain lightweight in the first implementation.

---

# Exit Trigger Output

The exit control layer should produce a structured exit trigger.

Suggested fields:

```text
exit_required
exit_reason
trigger_price
trigger_time
summary
```

Possible `exit_reason` values:

```text
target_reached
stop_loss_hit
deadline_reached
strategy_invalidated
```

Example:

```text
exit_required: true
exit_reason: target_reached
trigger_price: 106.12
trigger_time: 2026-03-14T18:20:00Z
summary: Profit target reached for SOLUSDT
```

---

# Re-evaluation Triggers

Not every market change should immediately trigger a re-evaluation.

The system should only re-evaluate when significant conditions occur.

Examples:

* large move toward stop-loss
* large move toward target
* deadline nearing
* abrupt momentum change
* account state update affecting trade viability

This phase should generate a **re-evaluation trigger**, not a new strategy by itself.

---

# Re-evaluation Trigger Output

Suggested structure:

```text
reevaluation_required
trigger_reason
trigger_time
priority
summary
```

Possible reasons:

```text
deadline_near
sharp_price_move
pnl_threshold_crossed
market_condition_changed
```

Example:

```text
reevaluation_required: true
trigger_reason: deadline_near
priority: high
summary: Trade has less than 2 hours remaining before deadline.
```

---

# Monitoring Decisions

At each monitoring cycle, the system should decide one of the following:

```text
continue_monitoring
trigger_exit
trigger_reevaluation
pause_due_to_state_issue
```

This decision should be persisted and logged.

---

# Monitoring State Persistence

Monitoring results should be stored so that the system can recover cleanly after restart.

Suggested table:

## `monitoring_events`

Fields:

```text
id
position_id
event_type
status
reason
current_price
pnl_percent
created_at
```

Possible `event_type` values:

```text
monitor_tick
exit_trigger
reevaluation_trigger
warning
```

This helps with:

* audit trail
* debugging
* restart continuity

---

# Monitoring Loop Flow

Recommended monitoring sequence:

```text
Load active position
   ↓
Fetch latest price
   ↓
Compute PnL and thresholds
   ↓
Check stop-loss
   ↓
Check target profit
   ↓
Check deadline
   ↓
Check re-evaluation triggers
   ↓
Persist monitoring result
   ↓
Return monitoring decision
```

This sequence should remain deterministic and easy to reason about.

---

# Multiple Positions

For MVP, the project should continue assuming:

```text
one active position at a time
```

This keeps monitoring simpler.

The monitoring loop should therefore focus on:

* zero active position → no-op
* one active position → monitor fully

Support for multiple concurrent positions can come later.

---

# CLI Behavior

The monitoring phase should support CLI visibility for current trade status.

Example commands:

```text
show active position
show monitoring status
show current pnl
```

Example output:

```text
Active Position
- Symbol: SOLUSDT
- Entry Price: 103.28
- Current Price: 105.10
- PnL: +1.76%
- Target: 4%
- Stop-Loss: 2%
- Deadline Remaining: 14 hours
- Status: monitoring
```

If an exit condition is reached:

```text
Monitoring Alert
- Symbol: SOLUSDT
- Exit Trigger: target_reached
- Current Price: 107.45
- Action: ready to close position
```

---

# Error Handling

The monitoring phase must handle:

* missing active position
* missing market price
* corrupted position state
* expired deadline with inconsistent state
* temporary API failures during price retrieval
* local scheduler interruption

Errors must:

* be logged
* avoid crashing the monitoring loop unnecessarily
* mark monitoring state clearly when incomplete

If monitoring cannot continue safely, the system should surface a warning and pause the automated monitoring state if needed.

---

# Logging Requirements

Log all meaningful monitoring actions.

Minimum logs:

* monitoring cycle started
* current price retrieved
* PnL calculated
* exit trigger created
* re-evaluation trigger created
* monitoring cycle completed
* monitoring warning or failure

Example logs:

```text
[INFO] Monitoring: Active position loaded for SOLUSDT
[INFO] Monitoring: Current price 105.10, PnL +1.76%
[INFO] ExitControl: No exit condition met
[WARN] Monitoring: Deadline near for SOLUSDT
```

---

# Suggested Modules

Suggested files for this phase:

```text
monitoring/
  loop.py
  evaluator.py
  scheduler.py
  events.py

exit_control/
  rules.py
  controller.py

models/
  monitoring_result.py
  exit_trigger.py
  reevaluation_trigger.py
```

Possible responsibilities:

## `loop.py`

* orchestrates each monitoring cycle

## `evaluator.py`

* calculates PnL and checks thresholds

## `scheduler.py`

* handles periodic loop scheduling

## `events.py`

* records monitoring events

## `controller.py`

* exit trigger decision logic

## `rules.py`

* target, stop-loss, and deadline checks

---

# Deliverables

Phase 8 is complete when:

* a periodic monitoring loop exists
* active positions can be monitored continuously
* PnL is calculated from current price and entry price
* target, stop-loss, and deadline exits are detected
* re-evaluation triggers are generated when needed
* monitoring events are logged and persisted

No external change reconciliation logic should be the focus here beyond what is needed to keep monitoring operational.

---

# Success Criteria

Phase 8 is successful when the system can:

* load an active position
* observe it at a fixed interval
* detect whether it should continue, re-evaluate, or exit
* persist and log monitoring state
* provide a clear monitoring decision for the next phase

```
```
