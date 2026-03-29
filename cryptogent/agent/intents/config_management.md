

````markdown id="config_intent_md"
# CONFIG MANAGEMENT INTENT

## Main Intent
`config_management`

---

## Description
Handles all configuration-related operations including API credentials, network mode (testnet/mainnet), and Binance-specific settings such as BNB burn.

---

## Sub-Intents

### 1. `config_show`
Retrieve current effective configuration.

### 2. `config_set_binance_mainnet_credentials`
Set Binance mainnet API credentials.

### 3. `config_set_binance_testnet_credentials`
Set Binance testnet API credentials.

### 4. `config_switch_to_testnet`
Enable Binance testnet mode.

### 5. `config_switch_to_mainnet`
Enable Binance mainnet mode.

### 6. `config_sync_bnb_burn_status`
Fetch and sync BNB burn status from Binance.

### 7. `config_enable_bnb_burn`
Enable paying fees with BNB.

### 8. `config_disable_bnb_burn`
Disable paying fees with BNB.

---

## Internal API Function Mapping

| Sub-Intent                          | Function Name                         |
|-----------------------------------|--------------------------------------|
| config_show                       | get_effective_config                 |
| config_set_binance_mainnet_credentials | set_mainnet_binance_credentials |
| config_set_binance_testnet_credentials | set_testnet_binance_credentials |
| config_switch_to_testnet          | enable_testnet_mode                  |
| config_switch_to_mainnet          | enable_mainnet_mode                  |
| config_sync_bnb_burn_status       | sync_bnb_burn_status                 |
| config_enable_bnb_burn            | set_bnb_burn                         |
| config_disable_bnb_burn           | set_bnb_burn                         |

---

## Function Specifications

---

### 1. get_effective_config

#### Description
Returns current configuration including network mode and settings.

#### Function Signature
`get_effective_config()`

#### Parameters
None

#### Output (Example)
```json
{
  "network": "testnet",
  "binance_api_configured": true,
  "bnb_burn_enabled": true
}
````

---

### 2. set_mainnet_binance_credentials

#### Description

Stores Binance mainnet API credentials.

#### Function Signature

`set_mainnet_binance_credentials(api_key, api_secret)`

#### Parameters

| Name       | Type   | Required | Description        |
| ---------- | ------ | -------- | ------------------ |
| api_key    | string | Yes      | Binance API key    |
| api_secret | string | Yes      | Binance API secret |

---

### 3. set_testnet_binance_credentials

#### Description

Stores Binance testnet API credentials.

#### Function Signature

`set_testnet_binance_credentials(api_key, api_secret)`

#### Parameters

| Name       | Type   | Required | Description        |
| ---------- | ------ | -------- | ------------------ |
| api_key    | string | Yes      | Testnet API key    |
| api_secret | string | Yes      | Testnet API secret |

---

### 4. enable_testnet_mode

#### Description

Switch system to Binance testnet.

#### Function Signature

`enable_testnet_mode()`

#### Parameters

None

---

### 5. enable_mainnet_mode

#### Description

Switch system to Binance mainnet.

#### Function Signature

`enable_mainnet_mode()`

#### Parameters

None

---

### 6. sync_bnb_burn_status

#### Description

Fetch BNB burn setting from Binance and update local config.

#### Function Signature

`sync_bnb_burn_status()`

#### Parameters

None

---

### 7. set_bnb_burn

#### Description

Enable or disable BNB burn.

#### Function Signature

`set_bnb_burn(enabled)`

#### Parameters

| Name    | Type    | Required | Description             |
| ------- | ------- | -------- | ----------------------- |
| enabled | boolean | Yes      | Enable/disable BNB burn |

---

## Tool Calling Schema

### config_show

```json
{
  "name": "get_effective_config",
  "arguments": {}
}
```

---

### config_set_binance_mainnet_credentials

```json
{
  "name": "set_mainnet_binance_credentials",
  "arguments": {
    "api_key": "string",
    "api_secret": "string"
  }
}
```

---

### config_set_binance_testnet_credentials

```json
{
  "name": "set_testnet_binance_credentials",
  "arguments": {
    "api_key": "string",
    "api_secret": "string"
  }
}
```

---

### config_switch_to_testnet

```json
{
  "name": "enable_testnet_mode",
  "arguments": {}
}
```

---

### config_switch_to_mainnet

```json
{
  "name": "enable_mainnet_mode",
  "arguments": {}
}
```

---

### config_sync_bnb_burn_status

```json
{
  "name": "sync_bnb_burn_status",
  "arguments": {}
}
```

---

### config_enable_bnb_burn

```json
{
  "name": "set_bnb_burn",
  "arguments": {
    "enabled": true
  }
}
```

---

### config_disable_bnb_burn

```json
{
  "name": "set_bnb_burn",
  "arguments": {
    "enabled": false
  }
}
```

---

## Validation Rules

* API credentials must not be empty
* Switching network should not break existing config
* BNB burn only valid if API is configured

---

## Intent Routing Rules

* "show config", "settings" → `config_show`
* "set api key", "connect binance" → credential intents
* "use testnet" → `config_switch_to_testnet`
* "use mainnet" → `config_switch_to_mainnet`
* "enable bnb burn" → `config_enable_bnb_burn`
* "disable bnb burn" → `config_disable_bnb_burn`

---

## Safety / Permission

| Sub-Intent      | Risk Level | Agent Allowed         |
| --------------- | ---------- | --------------------- |
| config_show     | Safe       | Yes                   |
| set credentials | High       | Restricted            |
| switch network  | High       | Requires confirmation |
| bnb burn toggle | Medium     | Yes                   |

---

## Notes

* Sensitive operations require confirmation layer
* API secrets should never be exposed in logs
* Prefer environment variables over plaintext storage

```
