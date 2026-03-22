from __future__ import annotations

from datetime import UTC, datetime


def utcnow_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def ms_to_utc_iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000.0, tz=UTC).replace(microsecond=0).isoformat()


def s_to_utc_iso(seconds: int) -> str:
    return datetime.fromtimestamp(seconds, tz=UTC).replace(microsecond=0).isoformat()
