````markdown
# EXCHANGE OPERATIONS INTENT

## Main Intent
`exchange_operations`

---

## Description
Handles read-only exchange-level operations such as connectivity checks, server time, exchange metadata, balances, and asset availability.  
These operations interact directly with Binance APIs but do not perform any trading actions.

---

## Sub-Intents

### 1. `exchange_ping`
Check connectivity with the exchange.

### 2. `exchange_time_query`
Retrieve exchange server time.

### 3. `exchange_info_query`
Retrieve exchange information (optionally for a specific symbol).

### 4. `exchange_balances_query`
Fetch live account balances from the exchange.

### 5. `exchange_assets_query`
List available trading assets.

### 6. `exchange_asset_check`
Check availability and trading pairs for a specific asset.

---

## Internal API Function Mapping

| Sub-Intent               | Function Name                     |
|-------------------------|----------------------------------|
| exchange_ping           | ping_exchange                    |
| exchange_time_query     | get_exchange_server_time         |
| exchange_info_query     | get_exchange_info                |
| exchange_balances_query | get_live_exchange_balances       |
| exchange_assets_query   | list_exchange_assets             |
| exchange_asset_check    | check_exchange_asset             |

---

## Function Specifications

---

### 1. ping_exchange

#### Description
Performs a simple connectivity check with the exchange.

#### Function Signature
`ping_exchange(testnet?, base_url?, tls_options?)`

#### Parameters

| Name        | Type   | Required | Description |
|-------------|--------|----------|------------|
| testnet     | bool   | No       | Use testnet instead of mainnet |
| base_url    | string | No       | Override base URL |
| tls_options | object | No       | TLS options (ca_bundle, insecure) |

#### Output
```json
{
  "status": "ok"
}
````

---

### 2. get_exchange_server_time

#### Description

Fetches the current server time from the exchange.

#### Function Signature

`get_exchange_server_time(testnet?, base_url?, tls_options?)`

#### Parameters

| Name        | Type   | Required | Description     |
| ----------- | ------ | -------- | --------------- |
| testnet     | bool   | No       | Use testnet     |
| base_url    | string | No       | Custom base URL |
| tls_options | object | No       | TLS options     |

#### Output

```json
{
  "server_time": 1712345678901
}
```

---

### 3. get_exchange_info

#### Description

Fetches exchange metadata including symbols and trading rules.

#### Function Signature

`get_exchange_info(symbol=None, testnet?, base_url?, tls_options?)`

#### Parameters

| Name        | Type   | Required | Description                           |
| ----------- | ------ | -------- | ------------------------------------- |
| symbol      | string | No       | Specific trading pair (e.g., BTCUSDT) |
| testnet     | bool   | No       | Use testnet                           |
| base_url    | string | No       | Custom base URL                       |
| tls_options | object | No       | TLS options                           |

#### Output

* Full exchange info or filtered symbol info

---

### 4. get_live_exchange_balances

#### Description

Retrieves live balances directly from the exchange.

#### Function Signature

`get_live_exchange_balances(show_all=False, testnet?, base_url?, tls_options?)`

#### Parameters

| Name        | Type   | Required | Description           |
| ----------- | ------ | -------- | --------------------- |
| show_all    | bool   | No       | Include zero balances |
| testnet     | bool   | No       | Use testnet           |
| base_url    | string | No       | Custom base URL       |
| tls_options | object | No       | TLS options           |

#### Output

```json
{
  "balances": [
    {
      "asset": "BTC",
      "free": "0.01",
      "locked": "0.00"
    }
  ]
}
```

---

### 5. list_exchange_assets

#### Description

Lists available trading assets.

#### Function Signature

`list_exchange_assets(limit=None, testnet?, base_url?, tls_options?)`

#### Parameters

| Name        | Type   | Required | Description          |
| ----------- | ------ | -------- | -------------------- |
| limit       | int    | No       | Max number of assets |
| testnet     | bool   | No       | Use testnet          |
| base_url    | string | No       | Custom base URL      |
| tls_options | object | No       | TLS options          |

#### Output

```json
{
  "assets": ["BTC", "ETH", "SOL"]
}
```

---

### 6. check_exchange_asset

#### Description

Checks if a specific asset is available and lists related trading pairs.

#### Function Signature

`check_exchange_asset(asset, limit=None, testnet?, base_url?, tls_options?)`

#### Parameters

| Name        | Type   | Required | Description              |
| ----------- | ------ | -------- | ------------------------ |
| asset       | string | Yes      | Asset symbol (e.g., BTC) |
| limit       | int    | No       | Limit results            |
| testnet     | bool   | No       | Use testnet              |
| base_url    | string | No       | Custom base URL          |
| tls_options | object | No       | TLS options              |

#### Output

```json
{
  "asset": "BTC",
  "available": true,
  "pairs": ["BTCUSDT", "BTCBUSD"]
}
```

---

## Tool Calling Schema

### exchange_ping

```json
{
  "name": "ping_exchange",
  "arguments": {}
}
```

---

### exchange_time_query

```json
{
  "name": "get_exchange_server_time",
  "arguments": {}
}
```

---

### exchange_info_query

```json
{
  "name": "get_exchange_info",
  "arguments": {
    "symbol": "optional string"
  }
}
```

---

### exchange_balances_query

```json
{
  "name": "get_live_exchange_balances",
  "arguments": {
    "show_all": false
  }
}
```

---

### exchange_assets_query

```json
{
  "name": "list_exchange_assets",
  "arguments": {
    "limit": "optional integer"
  }
}
```

---

### exchange_asset_check

```json
{
  "name": "check_exchange_asset",
  "arguments": {
    "asset": "string",
    "limit": "optional integer"
  }
}
```

---

## Validation Rules

* `asset` must be a valid symbol format
* API credentials required for balance queries
* TLS options must be valid if provided

---

## Intent Routing Rules

* "ping exchange", "connection check" → `exchange_ping`
* "server time", "exchange time" → `exchange_time_query`
* "exchange info", "symbol rules" → `exchange_info_query`
* "live balance", "account balance" → `exchange_balances_query`
* "list assets", "available coins" → `exchange_assets_query`
* "check asset BTC" → `exchange_asset_check`

---

## Safety / Permission

| Sub-Intent              | Risk Level | Agent Allowed              |
| ----------------------- | ---------- | -------------------------- |
| exchange_ping           | Safe       | Yes                        |
| exchange_time_query     | Safe       | Yes                        |
| exchange_info_query     | Safe       | Yes                        |
| exchange_balances_query | Medium     | Yes (requires credentials) |
| exchange_assets_query   | Safe       | Yes                        |
| exchange_asset_check    | Safe       | Yes                        |

---

## Notes

* All operations are read-only
* No trading actions performed
* Balance queries require authenticated access

```
```
