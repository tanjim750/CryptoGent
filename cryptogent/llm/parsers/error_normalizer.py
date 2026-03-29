from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ParseError:
    code: str
    message: str


def normalize_error(exc: Exception) -> ParseError:
    name = exc.__class__.__name__
    return ParseError(code=name, message=str(exc))
