from __future__ import annotations

import json

from cryptogent.llm.contracts import SchemaBundle


def format_schema(schema_bundle: SchemaBundle | None) -> str:
    if schema_bundle is None or schema_bundle.output_schema is None:
        return "Return a JSON object."
    schema_text = json.dumps(schema_bundle.output_schema, ensure_ascii=True, separators=(",", ":"))
    return "Return a JSON object that matches this schema exactly:\n" + schema_text
