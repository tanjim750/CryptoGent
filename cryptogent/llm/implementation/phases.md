````markdown
# FULL LLM LAYER ARCHITECTURE

## Overview
This document defines the full provider-agnostic LLM layer for CryptoGent.

The goal of this layer is to ensure that:
- prompt construction is isolated from agent logic
- context management works consistently across providers
- memory retrieval and token budgeting remain provider-independent
- provider switching does not require changes to upstream logic
- raw model output never reaches business logic directly
- every LLM task returns structured, validated, policy-checked output

This layer is not the agent layer.  
The agent only selects tasks and calls the LLM orchestrator.  
All LLM-specific responsibilities live inside this architecture.

---

## LLM Providers
- Openai
- Gemini
- Ollama (only for local)

# Architecture Goals

## Primary Goals
- provider independence
- stable prompt management
- controlled context window usage
- reusable memory integration
- structured output parsing
- strict validation before downstream usage
- traceability and auditability

## Secondary Goals
- easy prompt evolution
- model fallback support
- task-specific schema enforcement
- low coupling with business workflows
- testability with mock providers

---

# High-Level Flow

```text
Inputs + Relevant Memory
    ↓
Context Management Layer
    ↓
Token Policy Layer
    ↓
Prompt Construction Layer
    ↓
Provider Abstraction Layer
    ↓
Response Parsing Layer
    ↓
Validation & Policy Layer
    ↓
LLM Orchestrator
    ↓
Structured Final Result
    ↓
Audit / Trace Storage
````

---

# Suggested Main Modules

```text
llm/
  contracts/
  context/
  memory/
  prompts/
  providers/
  token_policy/
  parsers/
  validators/
  orchestration/
  audit/
```

---

# 1. LLM Integration Architecture

## Layer Position in Overall System

```text
Agent / Workflow Layer
    ↓
LLM Orchestrator
    ↓
Context Manager
    ↓
Memory Manager
    ↓
Token Policy
    ↓
Prompt Builder
    ↓
Provider Adapter
    ↓
Response Parser
    ↓
Validator / Policy
    ↓
Structured LLM Result
    ↓
Audit Trail
```

## Core Design Rule

Everything except the provider adapter must remain provider-agnostic.

That means:

* same context manager for OpenAI / Anthropic / local
* same memory retrieval logic
* same prompt builder
* same schema rules
* same validation layer
* only the provider adapter changes

## Core Interfaces

### Main Orchestrator Interface

```text
run_llm_task(task_name, context_input, memory_policy, schema_version, constraints) → LLMTaskResult
```

### Provider Interface

```text
LLMProvider.generate(request) → LLMRawResponse
```

### Prompt Builder Interface

```text
build_prompt(task_name, context_bundle, memory_bundle, schema_bundle, constraints) → PromptPackage
```

### Parser Interface

```text
parse_response(raw_response, schema_bundle) → ParsedLLMResult
```

### Validator Interface

```text
validate_llm_result(parsed_result, policy_bundle) → ValidationDecision
```

---

# 2. LLM Context Management

## Purpose

The Context Management Layer prepares task-specific context for the model.

It is responsible for:

* collecting structured inputs
* selecting relevant fields only
* compacting large upstream data
* formatting context consistently
* attaching memory
* preparing provider-safe context bundles

## Responsibilities

* gather raw input context
* merge upstream workflow outputs
* normalize field names
* drop irrelevant noise
* keep task-specific context minimal
* preserve important numeric and categorical values
* prepare context in stable schema form

## Inputs

Possible inputs may include:

* market summary
* sentiment summary
* technical indicators
* trade plan data
* execution candidate data
* portfolio state
* risk settings
* conversation context
* user constraints

## Output

```json
{
  "task": "market_analysis",
  "context_version": "v1",
  "core_context": {},
  "auxiliary_context": {},
  "memory_context": {},
  "metadata": {}
}
```

## Module Responsibilities

### `llm/context/context_manager.py`

Main entry point for context preparation.

### `llm/context/context_bundle.py`

Defines the normalized context bundle object.

### `llm/context/assemblers/`

Task-specific context assemblers.

Example:

* market_analysis_context_assembler.py
* trade_decision_context_assembler.py
* risk_assessment_context_assembler.py
* summarization_context_assembler.py

## Suggested Interfaces

### Context Manager

```text
build_context(task_name, raw_inputs, memory_bundle=None) → LLMContextBundle
```

### Task Context Assembler

```text
assemble_task_context(raw_inputs) → StructuredTaskContext
```

## Context Design Rules

* context must be structured, not raw free-form dumps
* only relevant data should be included
* upstream noise must be removed before prompting
* numeric values should remain machine-readable
* context should be stable across providers

---

# 3. Prompt Construction

## Purpose

The Prompt Construction Layer builds provider-agnostic prompts for all LLM tasks.

This layer is responsible for:

* system prompt
* task prompt
* schema instructions
* guardrails
* optional few-shot examples
* compact formatting
* prompt versioning

## Why It Must Be Separate

Prompt templates change frequently.
If prompt logic is mixed inside orchestration or business services:

* maintenance becomes hard
* prompt iteration becomes risky
* provider switching becomes messy
* testing becomes harder

## Inputs

* task name
* normalized context bundle
* memory bundle
* output schema bundle
* task constraints
* prompt version

## Output

```json
{
  "system_message": "...",
  "user_message": "...",
  "developer_message": "...",
  "prompt_version": "market_analysis_v3",
  "schema_version": "v1"
}
```

## Module Responsibilities

### `llm/prompts/builder.py`

Main prompt builder entry point.

### `llm/prompts/registry.py`

Maps task names to template versions.

### `llm/prompts/assembler.py`

Combines prompt parts into final package.

### `llm/prompts/schema_formatter.py`

Injects schema instructions.

### `llm/prompts/guardrails.py`

Provides task-specific guardrails.

### `llm/prompts/fewshot.py`

Optional few-shot example retrieval.

### `llm/prompts/templates/`

Stores versioned prompt templates.

Example:

```text
llm/prompts/templates/
  market_analysis/
    v1.txt
    v2.txt
  summarization/
    v1.txt
  trade_decision/
    v1.txt
```

## Suggested Interfaces

### Prompt Builder

```text
build_prompt(task_name, context_bundle, memory_bundle, schema_bundle, constraints) → PromptPackage
```

### Template Loader

```text
get_prompt_template(task_name, version=None) → PromptTemplate
```

### Schema Formatter

```text
format_schema(schema_bundle) → SchemaInstructionText
```

## Prompt Design Rules

* prompt builder must remain inside LLM layer
* prompt builder must not live inside agent layer
* prompts must be provider-agnostic
* prompts must always include output schema instruction
* prompts must always include safety/consistency guardrails
* prompt packages must be versioned

---

# 4. Provider Abstraction

## Purpose

The Provider Abstraction Layer isolates provider-specific APIs and request/response details.

It is responsible for:

* unified interface
* timeout handling
* retry logic
* rate limiting
* provider-specific parameter mapping
* JSON mode / structured output support
* model selection
* fallback provider switching

## Main Rule

Upstream layers must not know if the model is:

* OpenAI
* Anthropic
* local model
* fallback provider

They should only know:

* task name
* input prompt package
* expected structured result

## Module Responsibilities

### `llm/providers/base.py`

Defines `LLMProvider` interface.

### `llm/providers/openai_provider.py`

OpenAI implementation.

### `llm/providers/anthropic_provider.py`

Anthropic implementation.

### `llm/providers/local_provider.py`

Local model implementation.

### `llm/providers/fallback_provider.py`

Fallback chaining logic.

### `llm/providers/provider_registry.py`

Provider selection and registration.

## Core Interface

```text
class LLMProvider:
    generate(request: ProviderRequest) -> LLMRawResponse
```

## Input Request Example

```json
{
  "model": "provider-specific-model",
  "temperature": 0.2,
  "max_tokens": 1200,
  "system_message": "...",
  "user_message": "...",
  "developer_message": "...",
  "response_format": "json",
  "timeout_seconds": 30
}
```

## Output Example

```json
{
  "provider": "openai",
  "model": "gpt-x",
  "content": "...raw text...",
  "usage": {
    "input_tokens": 1200,
    "output_tokens": 250
  },
  "latency_ms": 1900,
  "finish_reason": "stop"
}
```

## Provider Rules

* no business logic inside provider adapters
* adapters only translate request/response format
* structured output mode should be used when available
* retry behavior must be configurable
* provider-specific failures must be normalized into common error types

---

# 5. Token Policy

## Purpose

The Token Policy Layer keeps requests inside safe context window size and applies deterministic trimming/compression rules.

It is responsible for:

* token estimation
* context window policy
* prompt size budgeting
* field-level prioritization
* truncation
* overflow prevention
* optional summarization fallback trigger

## Module Responsibilities

### `llm/token_policy/token_estimator.py`

Estimates token usage.

### `llm/token_policy/context_budgeter.py`

Assigns token budget by component.

### `llm/token_policy/truncation.py`

Trims low-priority sections when needed.

### `llm/token_policy/policies.py`

Defines task-specific token rules.

## Suggested Interface

```text
apply_token_policy(prompt_package, provider_capabilities, task_policy) → PromptPackage
```

## Priority Order Example

1. required schema instructions
2. critical context fields
3. required memory
4. optional examples
5. auxiliary detail

## Rules

* never truncate schema instruction
* never remove required context keys silently
* remove optional few-shot first when needed
* use deterministic trimming order
* keep provider-specific max context hidden from upstream layers
* provider context cap is a hard ceiling; task policy budget remains authoritative
* effective budget = min(task_policy_max_tokens, provider_context_cap)
* if base prompt (system + guardrails + schema) exceeds provider cap, warn or fail early
* never mutate task policy values based on provider caps (apply a runtime cap only)

---

# 6. LLM Memory

## Purpose

The Memory Layer retrieves only relevant memory for the current task.

It is responsible for:

* short-term task memory
* recent interaction memory
* task-specific contextual memory
* optional persistent strategy memory
* relevance filtering
* memory packaging for prompting
* pluggable persistence (sqlite/jsonl/txt/in-memory) configured in `cryptogent.toml`

## Memory Types

### Short-Term Memory

Current session or recent workflow context.

### Task Memory

Recent outputs relevant to the same task.

### Persistent Memory

Longer-term, non-sensitive structured memory if enabled.

## Module Responsibilities

### `llm/memory/memory_manager.py`

Main retrieval and packaging layer.

### `llm/memory/storage/`

Persistent memory store backends (sqlite, jsonl, txt) plus in-memory repository.

### `llm/memory/retrievers/`

Task-based or key-based memory retrieval.

### `llm/memory/filters.py`

Filters irrelevant memory.

### `llm/memory/memory_bundle.py`

Defines memory output bundle.

## Suggested Interface

```text
retrieve_memory(task_name, raw_inputs, conversation_state, retrieval_limit, memory_policy) → MemoryBundle
```

## Real Memory Store Architecture (Detailed)

### Overview

The memory store is a pluggable persistence layer used by `MemoryManager` to keep and retrieve chat/task memory.  
It supports multiple backends and a shared schema for memory items, with **isolation by `memory_key`** to avoid cross-session mixing.

### Components

**1. Storage Repository Interface**

All backends implement the same repository contract:

* `append(memory_key, items)` → persist new items
* `list_recent(memory_key, limit)` → fetch most recent items (ordered oldest → newest)

**2. Backends**

`llm/memory/storage/` provides:

* `sqlite_repository.py` — durable default, good for CLI and real sessions
* `jsonl_repository.py` — append-only JSONL, easy audit/inspection
* `txt_repository.py` — line-based text storage with JSON payload per line
* `in_memory_repository.py` — process‑local for ephemeral sessions/testing

**3. Factory**

`storage/factory.py` resolves a backend from `cryptogent.toml`:

```toml
[llm_memory]
backend = "sqlite"  # sqlite|jsonl|memory|txt
path = "llm_memory.sqlite3"
```

### Data Model

Each stored record contains:

* `memory_key` — session or conversation identifier
* `role` — `user` | `assistant` | `system`
* `content` — plain text content
* `timestamp` — ISO UTC time
* `metadata` — optional dict (backend may serialize)

### Memory Flow

1. **Append**  
   - CLI or orchestration appends new items by `memory_key`.
2. **Retrieve**  
   - `MemoryManager.retrieve_memory(...)` calls repository `list_recent(...)`.
3. **Filter/Normalize**  
   - Memory items are normalized and filtered by policy.
4. **Bundle**  
   - Final output is `MemoryBundle` (structured, provider‑independent).

### Isolation Rule

Memory is **always keyed**.  
Different workflows (CLI chat, test runs, real agents) must use different `memory_key` values to prevent leakage.

### Failure and Edge Cases

* If a backend fails, memory retrieval should return an empty bundle (not crash the task).
* SQLite is the only backend that supports multi-process durable state.
* In-memory backend is process‑local only; it resets on restart.
* JSONL/TXT are append‑only; if corrupted, retrieval should skip invalid lines.

## Rules

* memory must be relevant
* irrelevant memory must not be attached
* memory should be structured, not free-form dumps
* sensitive data should be filtered according to policy
* memory attachment must stay independent of provider

---

# 7. Response Parsing

## Purpose

The Response Parsing Layer converts raw model output into structured internal objects.

Raw LLM output must never directly enter business logic.

This layer is responsible for:

* JSON parsing
* schema validation
* missing fields detection
* malformed output handling
* coercion where safe
* normalized parse error reporting

## Module Responsibilities

### `llm/parsers/response_parser.py`

Main parser entry point.

### `llm/parsers/json_parser.py`

Strict JSON parsing.

### `llm/parsers/schema_parser.py`

Schema mapping and coercion.

### `llm/parsers/error_normalizer.py`

Normalizes parse failures.

## Suggested Interface

```text
parse_response(raw_response, schema_bundle) → ParsedLLMResult
```

## Output Example

```json
{
  "parsed": true,
  "data": {
    "market_bias": "bullish",
    "confidence": 0.72,
    "top_assets": ["BTCUSDT", "ETHUSDT"]
  },
  "errors": []
}
```

## Parse Rules

* invalid JSON must not pass silently
* missing required fields must be detected
* safe coercion only
* unknown fields may be preserved separately if needed
* parsing output must be deterministic

---

# 8. Validation & Policy

## Purpose

The Validation & Policy Layer checks whether parsed LLM output is usable.

It is responsible for:

* schema validity
* allowed symbols
* confidence presence
* vague reasoning detection
* hallucinated field detection
* risk/budget mismatch detection
* conflict with deterministic rule outputs
* accept / warn / reject / retry decision

## Possible Decisions

* accepted
* accepted_with_warning
* rejected
* retry_needed

## Module Responsibilities

### `llm/validators/result_validator.py`

Main validation entry point.

### `llm/validators/schema_validator.py`

Checks structural validity.

### `llm/validators/policy_validator.py`

Checks policy compatibility.

### `llm/validators/deterministic_conflict_validator.py`

Checks against deterministic outputs.

### `llm/validators/decision_models.py`

Validation result models.

## Suggested Interface

```text
validate_llm_result(parsed_result, validation_context) → ValidationDecision
```

## Output Example

```json
{
  "decision": "accepted_with_warning",
  "warnings": ["confidence_low", "thin_reasoning"],
  "errors": []
}
```

## Rules

* parsed output must not be trusted without validation
* business logic should consume only validated results
* rejected outputs must not flow downstream
* retry-needed decisions should include reason codes

---

# 9. LLM Orchestration

## Purpose

The Orchestration Layer coordinates the full LLM task lifecycle.

It is responsible for:

* receiving task request
* building context
* retrieving memory
* building prompt
* applying token policy
* calling provider
* parsing result
* validating result
* returning final structured output
* triggering audit logging

## Module Responsibilities

### `llm/orchestration/llm_orchestrator.py`

Main orchestration entry point.

### `llm/orchestration/task_runner.py`

Task-specific orchestration helpers.

### `llm/orchestration/retry_manager.py`

Handles structured retry policy.

### `llm/orchestration/result_builder.py`

Builds final task result object.

## Suggested Interface

```text
run_llm_task(task_name, raw_inputs, options=None) → LLMTaskResult
```

## Example Internal Flow

```text
1. build_context()
2. retrieve_memory()
3. build_prompt()
4. apply_token_policy()
5. provider.generate()
6. parse_response()
7. validate_result()
8. build_final_result()
9. write_audit_trace()
```

## Output Example

```json
{
  "status": "success",
  "task_name": "market_analysis",
  "result": {},
  "validation": {
    "decision": "accepted"
  },
  "metadata": {
    "prompt_version": "market_analysis_v3",
    "schema_version": "v1"
  }
}
```

---

# 10. Audit

## Purpose

The Audit Layer stores trace information for every LLM task.

It is responsible for:

* context snapshot metadata
* memory snapshot metadata
* prompt version
* schema version
* provider/model used
* raw output storage
* parsed result
* validation decision
* token usage
* latency
* retry history

## Module Responsibilities

### `llm/audit/audit_logger.py`

Main audit writer.

### `llm/audit/models.py`

Audit data structures.

### `llm/audit/repositories.py`

Persistence layer.

## Suggested Interface

```text
write_llm_trace(trace_record) → None
```

## Audit Record Example

```json
{
  "task_name": "market_analysis",
  "provider": "openai",
  "model": "gpt-x",
  "prompt_version": "market_analysis_v3",
  "schema_version": "v1",
  "validation_decision": "accepted",
  "latency_ms": 1900,
  "usage": {
    "input_tokens": 1200,
    "output_tokens": 250
  }
}
```

## Rules

* audit must not expose secrets
* prompt and response logging may be redacted depending on environment
* validation outcomes must always be logged
* retries should be traceable

---

# Contracts

## Suggested Contract Models

### `llm/contracts/provider_models.py`

* ProviderRequest
* ProviderCapabilities
* LLMRawResponse

### `llm/contracts/prompt_models.py`

* PromptPackage
* PromptTemplate
* SchemaBundle

### `llm/contracts/context_models.py`

* LLMContextBundle
* MemoryBundle

### `llm/contracts/result_models.py`

* ParsedLLMResult
* ValidationDecision
* LLMTaskResult

### `llm/contracts/task_models.py`

* LLMTaskName
* TaskConstraints
* TaskOptions

---

# Implementation Phases

## Phase 1 — Contracts and Interfaces

### Goal

Define all base contracts before implementation.

### Tasks

* define provider request/response models
* define prompt package models
* define context bundle models
* define memory bundle models
* define parsed result and validation models
* define final task result model
* define main interfaces for provider, parser, validator, orchestrator

### Deliverables

* `llm/contracts/`
* abstract interfaces in provider/parser/validator/orchestrator

---

## Phase 2 — Context Management

### Goal

Build stable context assembly.

### Tasks

* create context manager
* create task-specific assemblers
* normalize input field structure
* support task-based context bundles

### Deliverables

* `llm/context/`

---

## Phase 3 — Memory Layer

### Goal

Attach only relevant memory.

### Tasks

* create memory manager
* define retrieval policy
* define memory bundle format
* filter irrelevant memory

### Deliverables

* `llm/memory/`

---

## Phase 4 — Prompt Construction

### Goal

Implement full prompt builder.

### Tasks

* create prompt registry
* create prompt templates
* create schema formatter
* create guardrails builder
* create optional few-shot loader
* create prompt assembler
* support prompt versioning

### Deliverables

* `llm/prompts/`

---

## Phase 5 — Token Policy

### Goal

Protect context window and manage prompt size.

### Tasks

* implement token estimator
* implement budget allocator
* implement truncation rules
* add task-specific token policy

### Deliverables

* `llm/token_policy/`

---

## Phase 6 — Provider Adapters

### Goal

Implement provider abstraction.

### Tasks

* build base provider interface
* implement OpenAI adapter
* implement Gemini adapter
* implement Ollama adapter
* implement Anthropic adapter
* implement fallback adapter
* normalize provider responses

### Deliverables

* `llm/providers/`

---

## Phase 7 — Response Parsing

### Goal

Convert raw output into structured objects.

### Tasks

* build JSON parser
* build schema parser
* add parse error normalization
* support safe coercion rules

### Deliverables

* `llm/parsers/`

---

## Phase 8 — Validation & Policy

### Goal

Block unusable model outputs.

### Tasks

* build schema validator
* build output policy validator
* build deterministic conflict validator
* build final validation decision object

### Deliverables

* `llm/validators/`

---

## Phase 9 — Orchestration

### Goal

Connect all layers into one execution pipeline.

### Tasks

* implement LLM orchestrator
* implement retry manager
* implement final result builder
* wire all internal layers together

### Deliverables

* `llm/orchestration/`

---

## Phase 10 — Audit and Trace

### Goal

Make all LLM tasks debuggable and reviewable.

### Tasks

* build audit logger
* define trace models
* persist metadata and outcomes
* support redaction rules

### Deliverables

* `llm/audit/`

---

## Phase 11 — Testing and Stabilization

### Goal

Validate behavior before production integration.

### Tasks

* mock provider tests
* prompt builder tests
* token policy tests
* parser tests
* validator tests
* orchestrator integration tests
* fallback and retry tests

---

# Strict Rules

## Rule 1

Prompt construction must remain inside the LLM layer.

## Rule 2

Agent must not contain prompt templates.

## Rule 3

Only provider adapters may contain provider-specific logic.

## Rule 4

Raw LLM output must never reach business logic directly.

## Rule 5

Parsed output must always pass validation before downstream use.

## Rule 6

Memory and context must remain provider-independent.

## Rule 7

Token window handling must happen before provider call.

## Rule 8

Every LLM task must be auditable.

---

# Final Summary

The full LLM layer should be built as a provider-agnostic pipeline with the following stable order:

```text
contracts
→ context
→ memory
→ prompts
→ token_policy
→ providers
→ parsers
→ validators
→ orchestration
→ audit
```

This architecture ensures that:

* prompts stay isolated and maintainable
* provider switching remains easy
* context and memory remain reusable
* model outputs stay structured and safe
* all LLM tasks become testable, traceable, and production-ready

```
```
