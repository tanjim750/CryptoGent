from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BinanceCredentialUpdate:
    api_key: str | None = None
    api_secret: str | None = None
    base_url: str | None = None
    testnet: bool | None = None
    testnet_api_key: str | None = None
    testnet_api_secret: str | None = None
    spot_bnb_burn: bool | str | None = None
    testnet_spot_bnb_burn: bool | str | None = None


def _is_section(line: str) -> bool:
    s = line.strip()
    return s.startswith("[") and s.endswith("]") and len(s) >= 3


def _section_name(line: str) -> str:
    return line.strip()[1:-1].strip()


def _set_kv_in_section(lines: list[str], *, section: str, key: str, value_repr: str) -> list[str]:
    """
    Minimal TOML line editor:
    - Finds `[section]` and updates `key = ...` inside it.
    - Preserves comments/unknown keys/other sections as-is.
    - If section or key is missing, it is added.
    """
    out = lines[:]

    sec_start = None
    for i, line in enumerate(out):
        if _is_section(line) and _section_name(line) == section:
            sec_start = i
            break

    if sec_start is None:
        if out and out[-1].strip() != "":
            out.append("")
        out.append(f"[{section}]")
        out.append(f"{key} = {value_repr}")
        out.append("")
        return out

    # Find section end (next section header or EOF)
    sec_end = len(out)
    for j in range(sec_start + 1, len(out)):
        if _is_section(out[j]):
            sec_end = j
            break

    # Update existing key, if present
    needle = key.strip()
    for k in range(sec_start + 1, sec_end):
        raw = out[k]
        stripped = raw.lstrip()
        if stripped.startswith("#") or "=" not in stripped:
            continue
        left, _right = stripped.split("=", 1)
        if left.strip() == needle:
            indent = raw[: len(raw) - len(stripped)]
            out[k] = f"{indent}{needle} = {value_repr}"
            return out

    # Insert key near the top of the section (right after section header / any blank lines/comments).
    insert_at = sec_start + 1
    while insert_at < sec_end and out[insert_at].strip().startswith("#"):
        insert_at += 1
    out.insert(insert_at, f"{needle} = {value_repr}")
    return out


def _set_kv_in_block(
    lines: list[str], *, block_start: int, block_end: int, key: str, value_repr: str, insert_after: int | None = None
) -> list[str]:
    out = lines[:]
    if block_end > len(out):
        block_end = len(out)
    if block_end < block_start + 1:
        block_end = block_start + 1
    needle = key.strip()
    for k in range(block_start + 1, block_end):
        raw = out[k]
        stripped = raw.lstrip()
        if stripped.startswith("#") or "=" not in stripped:
            continue
        left, _right = stripped.split("=", 1)
        if left.strip() == needle:
            indent = raw[: len(raw) - len(stripped)]
            out[k] = f"{indent}{needle} = {value_repr}"
            return out

    insert_at = insert_after if insert_after is not None else block_start + 1
    if insert_at < block_start + 1 or insert_at > block_end:
        insert_at = block_start + 1
    out.insert(insert_at, f"{needle} = {value_repr}")
    return out


def _toml_str(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _toml_bool(value: bool) -> str:
    return "true" if value else "false"

def _toml_value(value: bool | str) -> str:
    if isinstance(value, bool):
        return _toml_bool(value)
    return _toml_str(value)


def _toml_int(value: int) -> str:
    return str(int(value))


def _toml_float(value: float) -> str:
    return str(float(value))


def _toml_list(values: list[str]) -> str:
    return "[" + ", ".join(_toml_str(v) for v in values) + "]"


def toml_str(value: str) -> str:
    return _toml_str(value)


def toml_bool(value: bool) -> str:
    return _toml_bool(value)


def toml_int(value: int) -> str:
    return _toml_int(value)


def toml_float(value: float) -> str:
    return _toml_float(value)


def update_binance_config(config_path: Path, update: BinanceCredentialUpdate) -> None:
    config_path = config_path.expanduser()
    raw = config_path.read_text(encoding="utf-8")
    lines = raw.splitlines()

    if update.base_url is not None:
        lines = _set_kv_in_section(lines, section="binance", key="base_url", value_repr=_toml_str(update.base_url))
    if update.testnet is not None:
        lines = _set_kv_in_section(lines, section="binance", key="testnet", value_repr=_toml_bool(update.testnet))
    if update.api_key is not None:
        lines = _set_kv_in_section(lines, section="binance", key="api_key", value_repr=_toml_str(update.api_key))
    if update.api_secret is not None:
        lines = _set_kv_in_section(lines, section="binance", key="api_secret", value_repr=_toml_str(update.api_secret))
    if update.testnet_api_key is not None:
        lines = _set_kv_in_section(lines, section="binance_testnet", key="api_key", value_repr=_toml_str(update.testnet_api_key))
    if update.testnet_api_secret is not None:
        lines = _set_kv_in_section(
            lines, section="binance_testnet", key="api_secret", value_repr=_toml_str(update.testnet_api_secret)
        )
    if update.spot_bnb_burn is not None:
        lines = _set_kv_in_section(lines, section="binance", key="spot_bnb_burn", value_repr=_toml_value(update.spot_bnb_burn))
    if update.testnet_spot_bnb_burn is not None:
        lines = _set_kv_in_section(
            lines, section="binance_testnet", key="spot_bnb_burn", value_repr=_toml_value(update.testnet_spot_bnb_burn)
        )

    # Always end with a newline.
    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def update_binance_credentials(config_path: Path, update: BinanceCredentialUpdate) -> None:
    # Backward-compatible alias.
    update_binance_config(config_path, update)


def update_config_value(
    config_path: Path,
    *,
    section: str,
    key: str,
    value_repr: str,
) -> None:
    config_path = config_path.expanduser()
    raw = config_path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    lines = _set_kv_in_section(lines, section=section, key=key, value_repr=value_repr)
    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def update_config_list(
    config_path: Path,
    *,
    section: str,
    key: str,
    values: list[str],
) -> None:
    update_config_value(config_path, section=section, key=key, value_repr=_toml_list(values))


def append_toml_table(
    config_path: Path,
    *,
    table: str,
    values: dict[str, object],
) -> None:
    config_path = config_path.expanduser()
    raw = config_path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    if lines and lines[-1].strip() != "":
        lines.append("")
    lines.append(f"[[{table}]]")
    for key, value in values.items():
        if isinstance(value, bool):
            value_repr = _toml_bool(value)
        elif isinstance(value, int):
            value_repr = _toml_int(value)
        else:
            value_repr = _toml_str(str(value))
        lines.append(f"{key} = {value_repr}")
    lines.append("")
    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def update_llm_model(
    config_path: Path,
    *,
    name: str,
    values: dict[str, str],
) -> None:
    config_path = config_path.expanduser()
    raw = config_path.read_text(encoding="utf-8")
    lines = raw.splitlines()

    def _is_table_header(line: str) -> bool:
        s = line.strip()
        return s.startswith("[") and s.endswith("]") and len(s) >= 3

    def _parse_name(line: str) -> str | None:
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            return None
        left, right = stripped.split("=", 1)
        if left.strip() != "name":
            return None
        val = right.strip()
        if val.startswith('"') and val.endswith('"') and len(val) >= 2:
            return val[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        if val.startswith("'") and val.endswith("'") and len(val) >= 2:
            return val[1:-1]
        return val

    target_start = None
    target_end = None
    name_line_idx = None
    i = 0
    while i < len(lines):
        if lines[i].strip() == "[[llm.models]]":
            block_start = i
            block_end = len(lines)
            for j in range(block_start + 1, len(lines)):
                if _is_table_header(lines[j]):
                    block_end = j
                    break
            for k in range(block_start + 1, block_end):
                parsed = _parse_name(lines[k])
                if parsed is not None:
                    if parsed == name:
                        target_start = block_start
                        target_end = block_end
                        name_line_idx = k
                    break
            if target_start is not None:
                break
            i = block_end
            continue
        i += 1

    if target_start is None:
        if lines and lines[-1].strip() != "":
            lines.append("")
        lines.append("[[llm.models]]")
        lines.append(f'name = "{name}"')
        for key, value_repr in values.items():
            if key == "name":
                continue
            lines.append(f"{key} = {value_repr}")
        lines.append("")
        config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    block_start = target_start
    block_end = target_end if target_end is not None else len(lines)
    insert_after = name_line_idx if name_line_idx is not None else block_start
    for key, value_repr in values.items():
        if key == "name":
            continue
        lines = _set_kv_in_block(
            lines,
            block_start=block_start,
            block_end=block_end,
            key=key,
            value_repr=value_repr,
            insert_after=insert_after + 1 if insert_after is not None else None,
        )
        if name_line_idx is not None and insert_after is not None:
            insert_after += 1
            block_end += 1

    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
