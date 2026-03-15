````markdown
# Phase 6 – Safety

This phase introduces the **pre-execution safety gate** of CryptoGent.

By this stage, the system should already be able to:

- collect structured trade input
- retrieve synchronized account state
- retrieve exchange metadata
- produce a trade plan with selected asset, approved budget, and strategy signal

Phase 6 ensures that no trade can proceed unless it is both:

- technically valid according to Binance Spot rules
- acceptable under the configured risk policies

This phase still does **not place orders**.  
It only decides whether a planned trade is safe and valid enough to become **execution-ready**.

---

# Phase Scope

This phase implements the following steps from the implementation roadmap:

25. deterministic validation  
26. risk management  

---

# Core Objective

After completing Phase 6, CryptoGent should be able to:

- validate trade parameters against Binance Spot rules
- validate balance and quantity constraints
- enforce risk management policies
- require stop-loss on every trade
- reject unsafe or invalid trade plans
- produce a final **approved or rejected execution candidate**

---

# Layers Covered in This Phase

This phase activates the following layers:

13. Deterministic Validation Layer  
14. Risk Management Layer  

Supporting layers involved:

4. Exchange Connection Layer  
5. Account State Synchronization Layer  
6. Local State, Persistence, and Recovery Layer  
3. User Preferences and Configuration Layer  
20. Audit, Logging, and Reporting Layer  

---

# Safety Philosophy

CryptoGent must never execute a trade solely because the user requested it or because a strategy generated a buy signal.

Every trade must pass through two independent gates:

1. **Deterministic Validation**
2. **Risk Management**

These gates must be enforced even if later phases introduce LLM advisory features.

---

# Deterministic Validation Layer

The Deterministic Validation Layer ensures that a proposed trade is **technically valid**.

This validation is based on:

- Binance Spot exchange rules
- current account state
- approved budget
- proposed order parameters

---

# Validation Inputs

Inputs include:

- trade request
- trade plan
- selected symbol
- approved budget
- account balances
- exchange info for the symbol
- current market price if needed for quantity estimation

---

# Required Exchange Metadata

This phase depends on symbol rules from:

```text
GET /api/v3/exchangeInfo
````

The following filters are especially important:

* `LOT_SIZE`
* `PRICE_FILTER`
* `MIN_NOTIONAL`
* `NOTIONAL` if present
* symbol trading `status`

The validation layer should work against normalized rule data, not raw exchange responses everywhere.

---

# Core Validation Checks

The validation layer must check at least the following.

## Symbol Exists

The selected symbol must exist in Binance Spot metadata.

---

## Symbol Trading Status

The symbol must be actively tradable.

Examples of acceptable state:

```text
TRADING
```

If not tradable, reject the trade.

---

## Supported Quote Asset

The selected symbol should be compatible with the configured exit or quote asset policy.

For MVP, strongly prefer:

```text
USDT quote pairs
```

---

## Balance Availability

The required balance must be available.

For a buy trade, the system must confirm that:

* free quote balance exists
* approved budget does not exceed available free balance

Do not use locked balance as spendable capital.

---

## Minimum Notional

The proposed order value must satisfy Binance minimum notional rules.

Example concept:

```text
price × quantity >= minNotional
```

If not satisfied, reject or adjust the candidate.

---

## Quantity Step Size

The proposed quantity must respect Binance step size.

Example:

* if step size is `0.001`
* quantity must align to that increment

The validation layer should normalize quantity if safe to do so.

---

## Price Tick Size

If a limit price is ever used, it must respect the symbol’s tick size.

For MVP, if using market orders first, this rule may still be implemented but not used heavily yet.

---

## Quantity Greater Than Zero

After all normalizations, quantity must remain valid and positive.

---

# Validation Output

The validation result should be structured.

Suggested fields:

```text
validation_status
validation_errors
normalized_quantity
normalized_price
validation_summary
```

Possible statuses:

```text
passed
failed
passed_with_adjustments
```

Example:

```text
validation_status: passed_with_adjustments
normalized_quantity: 1.234
validation_summary: Quantity rounded to step size.
```

---

# Validation Adjustments

The deterministic validation layer may make safe technical adjustments such as:

* rounding quantity to step size
* trimming price to tick size
* recalculating quantity after min notional checks

It must not make strategic or risk-based decisions.

Examples of what it must **not** do:

* choose a new asset
* change the user’s target
* increase budget
* ignore insufficient balance
* bypass symbol restrictions

---

# Risk Management Layer

The Risk Management Layer ensures that a technically valid trade is also **safely acceptable**.

This layer protects against:

* oversized exposure
* missing stop-loss
* bad reward-to-risk structure
* unreasonable deadline pressure
* repeated unsafe trades

---

# Risk Inputs

Inputs include:

* validated trade candidate
* trade request
* trade plan
* approved budget
* account balances
* open position state
* configuration limits
* user defaults and policies

---

# Core Risk Rules

The MVP risk layer should remain deterministic and explicit.

---

## Mandatory Stop-Loss

Every trade must include a stop-loss.

If stop-loss is missing, reject the trade.

This is mandatory.

---

## Stop-Loss Distance Must Be Reasonable

The stop-loss should not be effectively meaningless or excessively wide relative to the target.

A simple MVP rule may include:

* stop-loss must be greater than zero
* stop-loss should not exceed a configured maximum
* stop-loss should be logically compatible with the target profit

Example warning case:

```text
target profit = 3%
stop-loss = 10%
```

This may be technically valid but strategically poor.

---

## Maximum Position Size

The trade must not exceed the configured maximum share of account capital.

Example:

```yaml
trading:
  max_position_percent: 25
```

If the account has:

```text
1000 USDT free
```

then no single position should exceed:

```text
250 USDT
```

If the user requested more, the risk layer should either:

* reject
* or reduce according to policy

Conservative MVP behavior is preferred.

---

## Maximum Concurrent Positions

For MVP, CryptoGent should support:

```text
1 active position at a time
```

If an active position already exists, new trade approval should be blocked unless policy explicitly allows otherwise.

---

## Deadline Constraint

The trade must remain compatible with its deadline.

If the feasibility result already marked the request as:

```text
not_feasible
```

the risk layer should reject.

If the result is:

```text
feasible_with_warning
```

the risk layer may either:

* approve with warning
* reduce allocation
* reject if policy is strict

---

## Budget Protection

Even if deterministic validation passes, the trade should not consume too much capital under risky conditions.

For example, if feasibility is weak, the risk layer may reduce the final approved amount.

---

## Cooldown / Trade Lock Rules

For MVP, cooldown rules may remain simple but should be structurally supported.

Example future-ready rules:

* pause after repeated validation failures
* pause after risk rejection
* pause after stop-loss hit

At minimum, the design should allow such rules even if only partially used now.

---

# Risk Output

The risk result should also be structured.

Suggested fields:

```text
risk_status
risk_warnings
final_approved_budget
final_approved_quantity
risk_summary
```

Possible statuses:

```text
approved
approved_with_warning
rejected
```

Example:

```text
risk_status: approved_with_warning
final_approved_budget: 180
risk_warnings:
  - short_deadline
risk_summary: Approved with reduced exposure due to aggressive target horizon.
```

---

# Final Safety Decision

At the end of this phase, the system should produce an **Execution Candidate**.

Suggested structure:

```text
request_id
symbol
side
validation_status
risk_status
approved_budget
approved_quantity
target_profit_percent
stop_loss_percent
deadline_hours
execution_ready
summary
```

Example:

```text
request_id: tr_001
symbol: SOLUSDT
side: buy
validation_status: passed
risk_status: approved_with_warning
approved_budget: 180
approved_quantity: 1.742
target_profit_percent: 4
stop_loss_percent: 2
deadline_hours: 24
execution_ready: true
summary: Technically valid and approved with conservative allocation.
```

If rejected:

```text
execution_ready: false
```

and the summary should explain why.

---

# Persistence

This phase may persist safety decisions locally.

Suggested table:

## `execution_candidates`

Fields:

```text
id
request_id
symbol
side
validation_status
risk_status
approved_budget
approved_quantity
execution_ready
summary
created_at
updated_at
```

This is useful for:

* audit trail
* execution preparation
* recovery
* debugging

---

# CLI Behavior

After safety evaluation, the CLI should display a clear decision summary.

Example:

```text
Safety Evaluation Summary
- Symbol: SOLUSDT
- Validation: passed
- Risk: approved_with_warning
- Final Approved Budget: 180 USDT
- Final Quantity: 1.742
- Note: Timeline is aggressive, allocation reduced.

Continue to execution phase? [y/n]
```

If rejected:

```text
Safety Evaluation Summary
- Validation: failed
- Risk: rejected
- Reason: Budget below minimum notional requirement after normalization.
```

No execution should happen in this phase.

---

# Error Handling

This phase must handle:

* missing symbol rules
* invalid symbol metadata
* insufficient balance
* impossible quantity after rounding
* min notional failure
* missing stop-loss
* max position violations
* active position conflicts
* configuration inconsistencies

Errors must:

* be logged
* stop the flow safely
* return clear, deterministic explanations

---

# Logging Requirements

Log the following key events:

* deterministic validation started and completed
* validation adjustment made
* validation failed
* risk evaluation started and completed
* risk approval or rejection
* execution candidate created

Example logs:

```text
[INFO] Validation: Symbol SOLUSDT passed trading status check
[INFO] Validation: Quantity normalized to 1.742
[WARN] Risk: Allocation reduced due to aggressive target horizon
[INFO] Risk: Execution candidate approved
```

---

# Suggested Modules

Suggested files for this phase:

```text
validation/
  rules.py
  validator.py
  normalizer.py

risk/
  policies.py
  evaluator.py
  limits.py

models/
  validation_result.py
  risk_result.py
  execution_candidate.py
```

Possible responsibilities:

## `validator.py`

* orchestrates deterministic validation

## `rules.py`

* symbol rule checks
* balance checks
* min notional checks

## `normalizer.py`

* quantity and price normalization

## `evaluator.py`

* orchestrates risk decisions

## `policies.py`

* stop-loss policy
* max position policy
* deadline policy

## `limits.py`

* reusable limit calculations

---

# Deliverables

Phase 6 is complete when:

* deterministic validation works
* quantity and price normalization works where needed
* risk policies are enforced
* stop-loss is mandatory
* max position limits are enforced
* active position conflicts are handled
* an execution candidate can be produced or rejected safely

---

# Success Criteria

Phase 6 is successful when the system can:

* take a trade plan
* verify it against Binance Spot rules
* verify it against account state
* enforce deterministic risk controls
* produce a clear execution-ready candidate only when the trade is both valid and safe

```
```
