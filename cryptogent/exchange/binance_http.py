from __future__ import annotations

import json
import time
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from cryptogent.exchange.binance_errors import BinanceAPIError, BinanceAuthError


@dataclass(frozen=True)
class HTTPResponse:
    status: int
    data: object


def _parse_json(raw: bytes) -> object:
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def request_json(
    *,
    method: str,
    url: str,
    headers: dict[str, str] | None,
    timeout_s: float,
    ssl_context: ssl.SSLContext | None = None,
) -> HTTPResponse:
    req = urllib.request.Request(url=url, method=method.upper(), headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout_s, context=ssl_context) as resp:
            raw = resp.read()
            return HTTPResponse(status=int(resp.status), data=_parse_json(raw))
    except urllib.error.HTTPError as e:
        raw = e.read()
        data = _parse_json(raw)
        code = None
        msg = None
        if isinstance(data, dict):
            code = data.get("code")
            msg = data.get("msg")
        exc_cls = BinanceAuthError if e.code in (401, 403) else BinanceAPIError
        raise exc_cls(status=int(e.code), code=code, msg=msg, body=data) from None
    except urllib.error.URLError as e:
        # Normalize transport errors into a BinanceAPIError-like exception to simplify callers.
        raise BinanceAPIError(status=0, code=None, msg=str(e.reason), body=None) from None


def ms_timestamp() -> int:
    return int(time.time() * 1000)


def with_query(url: str, params: dict[str, str | int | float]) -> str:
    parsed = urllib.parse.urlsplit(url)
    existing = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    merged = list(existing) + [(k, str(v)) for k, v in params.items()]
    query = urllib.parse.urlencode(merged)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, query, parsed.fragment))
