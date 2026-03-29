````markdown
# SYSTEM INTENT

## Main Intent
`system`

---

## Description
Handles system-level operations such as initialization, status inspection, and interactive menu access.  
This intent is used for setting up the CryptoGent environment and checking system health/state.

---

## Sub-Intents

### 1. `system_initialize`
Initialize configuration file and database schema.

### 2. `system_menu_open`
Open the interactive CLI menu.

### 3. `system_status_query`
Retrieve system status and cached state summary.

---

## Internal API Function Mapping

| Sub-Intent          | Function Name           |
|--------------------|------------------------|
| system_initialize   | initialize_system      |
| system_menu_open    | open_interactive_menu  |
| system_status_query | get_system_status      |

---

## Function Specifications

---

### 1. initialize_system

#### Description
Creates a default configuration file (if missing) and initializes the SQLite database schema.

#### Function Signature
`initialize_system(config_path?, db_path?)`

#### Parameters

| Name        | Type   | Required | Description |
|------------|--------|----------|------------|
| config_path | string | No       | Custom config file path |
| db_path     | string | No       | Custom database file path |

#### Behavior
- Creates config file if it does not exist
- Initializes SQLite schema
- Does not overwrite existing config

#### Output
- Success message
- Created file paths

---

### 2. open_interactive_menu

#### Description
Opens the CLI interactive menu (primarily for human use).

#### Function Signature
`open_interactive_menu()`

#### Parameters
None

#### Behavior
- Starts interactive session
- Requires human interaction

#### Output
- Menu session started

#### Notes
- Not recommended for agent usage (human-only interaction)

---

### 3. get_system_status

#### Description
Returns system status including config path, database path, and cached state summary.

#### Function Signature
`get_system_status()`

#### Parameters
None

#### Behavior
- Returns config path
- Returns database path
- Returns cached balances count
- Returns cached open orders count
- Returns last sync status

#### Output (Example)
```json
{
  "config_path": "./cryptogent.toml",
  "db_path": "./cryptogent.sqlite3",
  "balances_count": 5,
  "open_orders_count": 2,
  "last_sync_status": "success"
}
````

---

## Tool Calling Schema

### system_initialize

```json
{
  "name": "initialize_system",
  "arguments": {
    "config_path": "optional string",
    "db_path": "optional string"
  }
}
```

---

### system_menu_open

```json
{
  "name": "open_interactive_menu",
  "arguments": {}
}
```

---

### system_status_query

```json
{
  "name": "get_system_status",
  "arguments": {}
}
```

---

## Validation Rules

* `system_initialize`:

  * config_path and db_path are optional
  * must not overwrite existing config

* `system_menu_open`:

  * should not be triggered by agent automatically
  * requires human interaction

* `system_status_query`:

  * safe read-only operation

---

## Intent Routing Rules

* "init", "setup", "initialize system" → `system_initialize`
* "menu", "open menu", "interactive mode" → `system_menu_open`
* "status", "system status", "current state" → `system_status_query`

---

## Safety / Permission

| Sub-Intent          | Risk Level | Agent Allowed                |
| ------------------- | ---------- | ---------------------------- |
| system_initialize   | Low        | Yes                          |
| system_menu_open    | Medium     | Restricted (human preferred) |
| system_status_query | Safe       | Yes                          |

---

## Notes

* No trading-related side effects
* Pure system-level operations
* Safe except interactive menu

```
