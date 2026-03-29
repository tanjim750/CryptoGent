from __future__ import annotations

import json

from cryptogent.llm.contracts import SchemaBundle


def build_fewshot(schema_bundle: SchemaBundle | None) -> str:
    if schema_bundle is None or not schema_bundle.examples:
        return ""
    lines: list[str] = ["Examples:"]
    for ex in schema_bundle.examples:
        lines.append(json.dumps(ex, ensure_ascii=True, separators=(",", ":")))
    return "\n".join(lines)
