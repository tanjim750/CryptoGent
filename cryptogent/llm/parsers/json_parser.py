from __future__ import annotations

import json
from typing import Any


def parse_json(text: str) -> dict[str, Any]:
    if not text or not text.strip():
        raise ValueError("Empty response content")
    try:
        data = json.loads(text)
    except Exception:
        data = json.loads(_extract_json_object(text))
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")
    return data


def _extract_json_object(text: str) -> str:
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found")
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise ValueError("Unterminated JSON object")
