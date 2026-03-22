from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from cryptogent.util.time import s_to_utc_iso, utcnow_iso


class FearGreedAPIError(RuntimeError):
    pass


@dataclass(frozen=True)
class FearGreedReading:
    value: int
    value_classification: str
    timestamp_utc: str
    time_until_update_s: int | None


@dataclass(frozen=True)
class FearGreedResponse:
    source: str
    reading: FearGreedReading
    raw: dict


def _build_ssl_context(*, ca_bundle: Path | None, insecure: bool) -> ssl.SSLContext | None:
    if insecure:
        return ssl._create_unverified_context()
    if ca_bundle is None:
        return None
    ctx = ssl.create_default_context()
    ctx.load_verify_locations(cafile=str(ca_bundle.expanduser()))
    return ctx


def _parse_int(value: object, *, field: str) -> int:
    try:
        return int(str(value))
    except Exception as exc:
        raise FearGreedAPIError(f"Invalid {field} value: {value!r}") from exc


def fetch_fear_greed(
    *,
    limit: int = 1,
    timeout_s: float = 10.0,
    ca_bundle: Path | None = None,
    insecure: bool = False,
) -> FearGreedResponse:
    base_url = "https://api.alternative.me/fng/"
    query = urllib.parse.urlencode({"limit": str(limit), "format": "json"})
    url = f"{base_url}?{query}"
    ssl_context = _build_ssl_context(ca_bundle=ca_bundle, insecure=insecure)
    req = urllib.request.Request(url=url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout_s, context=ssl_context) as resp:
            raw_bytes = resp.read()
    except urllib.error.HTTPError as exc:
        raise FearGreedAPIError(f"HTTP error {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise FearGreedAPIError(f"Network error: {exc.reason}") from exc

    try:
        payload = json.loads(raw_bytes.decode("utf-8"))
    except Exception as exc:
        raise FearGreedAPIError("Non-JSON response from API") from exc

    data = payload.get("data")
    if not isinstance(data, list) or not data:
        raise FearGreedAPIError("API returned no data")

    first = data[0] if isinstance(data[0], dict) else None
    if not isinstance(first, dict):
        raise FearGreedAPIError("Unexpected data shape")

    value = _parse_int(first.get("value"), field="value")
    classification = str(first.get("value_classification") or "").strip()
    if not classification:
        raise FearGreedAPIError("Missing value_classification")

    timestamp_s = _parse_int(first.get("timestamp"), field="timestamp")
    timestamp_utc = s_to_utc_iso(timestamp_s) if timestamp_s > 0 else utcnow_iso()

    time_until_update_s: int | None = None
    if "time_until_update" in first and first.get("time_until_update") not in (None, ""):
        try:
            time_until_update_s = int(str(first.get("time_until_update")))
        except Exception:
            time_until_update_s = None

    reading = FearGreedReading(
        value=value,
        value_classification=classification,
        timestamp_utc=timestamp_utc,
        time_until_update_s=time_until_update_s,
    )
    return FearGreedResponse(source="alternative.me", reading=reading, raw=payload)
