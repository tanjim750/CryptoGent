````markdown
# AGENTIC ROUTING IMPLEMENTATION GUIDE

## Objective
Implement a two-layer agentic routing system for CryptoGent where:

1. The **High-Level Orchestrator** understands the user request, detects main intent and sub-intents, extracts entities, and decides the routing strategy.
2. The **Execution Orchestrator** runs the internal workflow step-by-step using internal API functions and returns structured results.
3. Specialized workflows such as **market intelligence** run as hidden internal agentic flows and return structured outputs back to the High-Level Orchestrator.

---

# Core Design Principles

## 1. Strict Two-Layer Separation
- High-Level Orchestrator must not execute low-level business logic
- Execution Orchestrator must not generate user-facing final answers directly

## 2. Intent-Driven Routing
- Every user request must resolve into:
  - one main intent
  - one or more sub-intents
  - optional routing strategy
  - optional execution dependencies

## 3. Internal APIs Only
- Agent must call internal application APIs/functions
- Agent must never generate or execute CLI commands directly

## 4. Structured Outputs Everywhere
- Each workflow step must return machine-readable structured results
- Final response composition happens only in the High-Level Orchestrator

## 5. Safety First
- Manual and human-only actions must be blocked
- High-risk actions must pass confirmation and policy gates
- Trading execution must remain deterministic and validated

---

# Recommended Folder Structure

```text
cryptogent/
  agent/
    high_level/
      intent_classifier.py
      sub_intent_detector.py
      entity_extractor.py
      routing_strategy.py
      response_builder.py
      conversation_state.py

    execution/
      workflow_executor.py
      step_executor.py
      parameter_resolver.py
      failure_handler.py
      workflow_registry.py

    policies/
      permission_policy.py
      confirmation_policy.py
      human_only_guard.py
      safety_guard.py

    contracts/
      intent_models.py
      routing_models.py
      workflow_models.py
      result_models.py

  workflows/
    system/
    config/
    exchange/
    sync/
    local_data/
    market_intelligence/
    trade_request/
    trade_planning/
    trade_execution/
    manual_orders/
    manual_loops/
    positions/
    monitoring/
    order_management/
    reliability/
    pnl/
    dust/

  services/
    internal_api/
      system_service.py
      config_service.py
      exchange_service.py
      sync_service.py
      local_data_service.py
      market_service.py
      trade_request_service.py
      trade_plan_service.py
      execution_service.py
      position_service.py
      monitoring_service.py
      reliability_service.py
      pnl_service.py
      dust_service.py
````

---

# Phase Plan

## Phase 1 — Foundation Contracts

### Goal

Define all common models, enums, and contracts before implementation.

### Tasks

* Define main intents enum
* Define sub-intents enum
* Define routing strategy enum
* Define workflow result schema
* Define step result schema
* Define failure result schema
* Define conversation state schema
* Define permission/confirmation result schema

### Deliverables

* `intent_models.py`
* `routing_models.py`
* `workflow_models.py`
* `result_models.py`

### Exit Criteria

* All routing-related types are locked
* No business logic yet
* All future modules depend on these contracts

---

## Phase 2 — High-Level Orchestrator Skeleton

### Goal

Build the top-layer user-facing routing brain.

### Tasks

* Implement `classify_user_intent`
* Implement `extract_request_entities`
* Implement `detect_sub_intents`
* Implement `decide_routing_strategy`
* Implement `build_user_response`
* Implement initial conversation state reader/writer

### Required Components

* `intent_classifier.py`
* `sub_intent_detector.py`
* `entity_extractor.py`
* `routing_strategy.py`
* `response_builder.py`
* `conversation_state.py`

### Deliverables

* High-Level Orchestrator can:

  * classify requests
  * extract entities
  * produce routing plan
  * return direct response for simple queries

### Exit Criteria

* Input user message → returns main intent, sub-intents, entities, routing plan

---

## Phase 3 — Execution Orchestrator Skeleton

### Goal

Build the internal workflow engine that runs sub-intents step-by-step.

### Tasks

* Implement workflow registry
* Implement step executor
* Implement parameter resolver
* Implement workflow executor
* Implement basic failure handler

### Required Components

* `workflow_registry.py`
* `step_executor.py`
* `parameter_resolver.py`
* `workflow_executor.py`
* `failure_handler.py`

### Deliverables

* Execution Orchestrator can:

  * receive routing plan
  * resolve parameters
  * execute sequential steps
  * store intermediate results
  * return aggregated structured result

### Exit Criteria

* Multi-step flow works with mocked internal APIs

---

## Phase 4 — Workflow Registry and Intent Mapping

### Goal

Map each sub-intent to internal API functions and execution metadata.

### Tasks

* Register all main intents
* Register all sub-intents
* Define which sub-intents are:

  * read-only
  * mutating
  * sensitive
  * human-only
* Define execution order templates for multi-step flows

### Deliverables

* `workflow_registry.py` filled with all mappings
* intent → sub-intent → internal function map
* policy metadata attached per sub-intent

### Exit Criteria

* Router can resolve any supported sub-intent into an executable internal function definition

---

## Phase 5 — Policy and Safety Layer

### Goal

Protect the system from unsafe or forbidden actions.

### Tasks

* Implement human-only guard
* Implement confirmation policy
* Implement permission policy
* Implement execution pre-checks
* Implement blocked-action response builder

### Required Components

* `permission_policy.py`
* `confirmation_policy.py`
* `human_only_guard.py`
* `safety_guard.py`

### Rules to Enforce

* Manual orders blocked
* Manual loops blocked
* Execution requires confirmation
* Cancellation requires confirmation
* Sensitive config actions require confirmation

### Exit Criteria

* Every workflow step passes through policy layer before execution

---

## Phase 6 — System, Config, Exchange, Sync, and Local Data Workflows

### Goal

Implement low-risk foundational workflows first.

### Workflows

* system
* config_management
* exchange_operations
* sync_operations
* local_data_query

### Tasks

* Build workflow adapters for each main intent
* Wire sub-intents to internal services
* Normalize outputs into common workflow result schema

### Deliverables

* Safe non-trading workflows fully operational

### Exit Criteria

* Agent can answer:

  * system status
  * config show
  * exchange ping/info/balance
  * sync actions
  * local cached data queries

---

## Phase 7 — Trade Request and Planning Workflows

### Goal

Implement pre-execution trading flows.

### Workflows

* trade_request_management
* trade_planning

### Tasks

* Create workflow adapters for:

  * create request
  * list request
  * show request
  * cancel request
  * validate request
  * build trade plan
  * list plans
  * show plan
  * safety check
  * candidate review

### Important

* No exchange order placement in this phase
* Only staged artifacts and safety outputs

### Exit Criteria

* Agent can create and validate requests
* Agent can build plans and produce execution candidates

---

## Phase 8 — Trade Execution and Order Management Workflows

### Goal

Implement exchange-side operational workflows.

### Workflows

* trade_execution
* order_management

### Tasks

* Execute approved candidate
* List and show executions
* Cancel execution
* Reconcile executions
* Cancel eligible open orders

### Safety Requirements

* Must go through confirmation policy
* Must verify candidate state
* Must verify cancellability

### Exit Criteria

* Agent can safely execute approved candidate flows with policy enforcement

---

## Phase 9 — Position, Monitoring, PnL, Dust Workflows

### Goal

Implement all read-heavy portfolio workflows.

### Workflows

* position_management
* monitoring
* pnl_management
* dust_management

### Tasks

* list/show positions
* live review
* monitoring once/loop/events
* realized and unrealized pnl
* dust ledger inspection

### Exit Criteria

* Agent can inspect current state and profitability clearly

---

## Phase 10 — Reliability Management Workflow

### Goal

Implement system recovery and automation pause/resume control.

### Workflow

* reliability_management

### Tasks

* reliability status
* reconciliation
* resume global
* resume symbol
* resume loop
* reliability events

### Safety Requirements

* resume actions must be confirmation-gated
* reconciliation may modify pause scopes
* global/symbol/loop scope must remain distinct

### Exit Criteria

* Agent can inspect and recover automation state safely

---

## Phase 11 — Market Intelligence Hidden Workflow

### Goal

Implement the internal agentic flow for market analysis.

### Workflow

* market_intelligence

### Internal Steps

1. search planning
2. provider query generation
3. fetch market news/social data
4. normalization
5. deduplication
6. clustering
7. top-k ranking
8. cleaning
9. chunking
10. chunk summarization
11. sentiment synthesis
12. technical context merge
13. final market decision generation
14. deterministic validation
15. return structured analysis result

### Required Modules

* market search planner
* provider query builders
* data fetch orchestrator
* normalization pipeline
* deduplication pipeline
* ranking pipeline
* summarization pipeline
* synthesis pipeline
* final decision builder

### Exit Criteria

* `market_analysis`, `asset_analysis`, `asset_ranking`, `market_opportunity_discovery` work end-to-end

---

## Phase 12 — Multi-Intent and Conditional Routing

### Goal

Support user requests that require multiple sub-intents and branching.

### Examples

* create trade request → validate → build plan
* analyze asset → assess risk
* market analysis → opportunity discovery
* show request → validate if still pending

### Tasks

* support chained routing plans
* support previous-step output injection
* support conditional next-step execution

### Exit Criteria

* Complex user requests can be handled in one pass

---

## Phase 13 — Conversation State and Reference Resolution

### Goal

Allow short follow-up commands like:

* "validate it"
* "show the last one"
* "execute that candidate"

### Tasks

* persist recent ids:

  * trade_request_id
  * plan_id
  * candidate_id
  * execution_id
  * position_id
  * loop_id
* resolve pronoun/reference-based follow-ups
* attach recent symbols and budgets to context

### Exit Criteria

* Follow-up routing works without forcing repeated user input

---

## Phase 14 — Failure Handling and Recovery

### Goal

Make agentic routing robust.

### Tasks

* define retryable vs non-retryable failures
* standardize error result schema
* add safe fallbacks
* add partial success handling
* add missing-parameter detection
* add graceful clarification prompts only when needed

### Exit Criteria

* Workflow failures do not break the whole orchestration chain

---

## Phase 15 — Testing and Validation

### Goal

Ensure routing reliability before production usage.

### Test Types

* intent classification tests
* entity extraction tests
* routing plan tests
* single-step execution tests
* multi-step workflow tests
* policy block tests
* confirmation gate tests
* conversation memory resolution tests
* market intelligence hidden workflow tests

### Deliverables

* unit tests
* integration tests
* mock internal API tests
* golden routing test cases

### Exit Criteria

* Full routing system behaves deterministically and safely

---

# Implementation Order Recommendation

## Recommended Build Order

1. Phase 1
2. Phase 2
3. Phase 3
4. Phase 4
5. Phase 5
6. Phase 6
7. Phase 7
8. Phase 8
9. Phase 9
10. Phase 10
11. Phase 11
12. Phase 12
13. Phase 13
14. Phase 14
15. Phase 15

---

# MVP Scope Recommendation

If you want a smaller first milestone, implement:

* Phase 1 to Phase 7
* plus read-only parts of Phase 9
* keep market intelligence simplified
* skip manual workflows entirely except detection/blocking
* add execution later after full testing

---

# Hard Rules to Lock Before Coding

## Rule 1

High-Level Orchestrator never performs business execution directly.

## Rule 2

Execution Orchestrator never produces final user-facing prose directly.

## Rule 3

All workflow steps must return structured results.

## Rule 4

Manual order and manual loop actions are always blocked for agent execution.

## Rule 5

Trade execution must require approved candidate + policy pass + confirmation pass.

## Rule 6

Market intelligence must run as a hidden internal workflow, not direct free-form LLM response.

---

# Suggested Milestone Outputs

## Milestone A

Intent classification + routing skeleton works

## Milestone B

Safe read-only workflows work

## Milestone C

Trade request and planning flows work

## Milestone D

Execution and cancellation flows work with safeguards

## Milestone E

Market intelligence hidden workflow works end-to-end

## Milestone F

Conversation memory and multi-step follow-up routing work

```
```
