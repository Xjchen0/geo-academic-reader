#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A polite, patient HTTP JSON client for public metadata APIs.

Why this module exists
----------------------
Crossref is a free public API, and it rate-limits. A single misbehaving
response - HTTP 429 with an HTML body, or a 503 from a proxy - used to reach
the agent as an opaque ``Expecting value: line 1 column 1 (char 0)`` traceback.
The agent then filled the gap with a DOI it had never resolved, which is the
one thing the verification route exists to prevent.

The rules this module enforces:

* **Retry only what is worth retrying.** 429 and 5xx are transient; 404 is
  final. Retrying a 404 just wastes the polite quota.
* **Back off exponentially** and honour ``Retry-After`` when the server sends
  it. Crossref answers a rate-limited request with that header.
* **Never raise.** Every failure comes back as a dict with a machine-readable
  ``kind``, so the caller can tell "this DOI does not exist" apart from
  "Crossref is busy" - the difference between a candidate that will never
  verify and one that will verify on the next run.
* **Say who you are.** The ``User-Agent`` carries the app and, when the user
  gave one, a ``mailto`` address, which is Crossref's polite pool.
* **Leave a gap between calls.** Verifying 25 references in a tight loop is
  how a workspace gets itself throttled.
"""

import time
from typing import Callable, Dict, Optional

import requests

from .config import DEFAULT_HEADERS

# Status codes worth trying again. 429 is the rate limiter; 5xx is the
# server having a bad day.
RETRYABLE_STATUS = (429, 500, 502, 503, 504)

# Failure kinds. The caller branches on these, so keep them stable.
KIND_OK = "ok"
KIND_NOT_FOUND = "not_found"
KIND_RATE_LIMITED = "rate_limited"
KIND_SERVER_ERROR = "server_error"
KIND_NETWORK = "network"
KIND_BAD_JSON = "bad_json"
KIND_OTHER = "other"

DEFAULT_RETRIES = 4
DEFAULT_BACKOFF = 1.6
DEFAULT_TIMEOUT = 25
# A courtesy gap between calls. Small, but it keeps a 25-item verification
# run out of the throttled bucket.
DEFAULT_DELAY = 0.2

# Timestamp of the last request this module issued. Used to keep the gap
# between calls even when each call is made separately - verifying 25
# references one at a time is exactly the pattern that gets a workspace
# throttled.
_LAST_REQUEST_AT = [0.0]


def reset_rate_limit() -> None:
    """Forget the last request time (tests, and long pauses)."""
    _LAST_REQUEST_AT[0] = 0.0


def build_headers(mailto: str = "", accept: str = "application/json") -> Dict[str, str]:
    """Headers for a metadata API: honest User-Agent, optional mailto."""
    headers = dict(DEFAULT_HEADERS)
    headers["Accept"] = accept
    user_agent = headers.get("User-Agent", "")
    if mailto:
        headers["User-Agent"] = "{} (mailto:{})".format(user_agent, mailto)
        # Crossref's polite pool also accepts a From header.
        headers["From"] = mailto
    return headers


def _retry_after_seconds(response, fallback: float) -> float:
    """Honour Retry-After when the server sends it (seconds or a date)."""
    raw = ""
    try:
        raw = response.headers.get("Retry-After", "") or ""
    except Exception:  # pragma: no cover - defensive, headers may be absent
        raw = ""
    if not raw:
        return fallback
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        pass
    try:
        from email.utils import parsedate_to_datetime

        when = parsedate_to_datetime(raw)
        import datetime as _dt

        now = _dt.datetime.now(_dt.timezone.utc)
        if when.tzinfo is None:
            when = when.replace(tzinfo=_dt.timezone.utc)
        return max(0.0, (when - now).total_seconds())
    except Exception:
        return fallback


def request_json(
    url: str,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
    backoff: float = DEFAULT_BACKOFF,
    mailto: str = "",
    delay: float = DEFAULT_DELAY,
    sleeper: Optional[Callable[[float], None]] = None,
    session: Optional[requests.Session] = None,
) -> Dict[str, object]:
    """GET a JSON endpoint. Returns a dict; never raises.

    Success: ``{"ok": True, "data": <parsed json>, "status": 200, ...}``
    Failure: ``{"ok": False, "error": "<message>", "kind": "<kind>", ...}``
    """
    sleep = sleeper if sleeper is not None else time.sleep
    request_headers = dict(headers) if headers else build_headers(mailto)
    query = dict(params or {})
    if mailto and "mailto" not in query:
        query["mailto"] = mailto

    attempts = max(1, int(retries))
    last_error = ""
    last_kind = KIND_OTHER
    last_status = 0

    for attempt in range(1, attempts + 1):
        if delay:
            # Keep a gap between requests, across calls as well as within
            # one. Verifying 25 references one at a time is exactly the
            # pattern that gets a workspace throttled.
            now = time.monotonic()
            waited = delay - (now - _LAST_REQUEST_AT[0])
            if waited > 0:
                sleep(waited)
            _LAST_REQUEST_AT[0] = time.monotonic()
        getter = session.get if session is not None else requests.get
        try:
            response = getter(url, params=query, headers=request_headers, timeout=timeout)
        except Exception as exc:
            last_error = "{}: {}".format(type(exc).__name__, exc)
            last_kind = KIND_NETWORK
            last_status = 0
            if attempt < attempts:
                sleep(backoff ** attempt)
                continue
            break

        status = int(getattr(response, "status_code", 0) or 0)
        last_status = status

        if status == 404:
            return {
                "ok": False,
                "error": "404 Not Found",
                "kind": KIND_NOT_FOUND,
                "status": status,
                "attempts": attempt,
                "url": url,
            }

        if status in RETRYABLE_STATUS:
            last_kind = KIND_RATE_LIMITED if status == 429 else KIND_SERVER_ERROR
            last_error = "HTTP {} ({})".format(status, last_kind)
            if attempt < attempts:
                wait = _retry_after_seconds(response, backoff ** attempt)
                sleep(min(max(wait, 0.0), 60.0))
                continue
            break

        if status >= 400:
            return {
                "ok": False,
                "error": "HTTP {}".format(status),
                "kind": KIND_OTHER,
                "status": status,
                "attempts": attempt,
                "url": url,
            }

        try:
            data = response.json()
        except Exception as exc:
            # A body that is not JSON is usually a rate-limit page or a proxy
            # error page. Say so instead of leaking a decoder traceback.
            last_kind = KIND_BAD_JSON
            last_error = "响应不是 JSON（{}）".format(type(exc).__name__)
            body = ""
            try:
                body = (response.text or "")[:160]
            except Exception:
                body = ""
            if attempt < attempts:
                sleep(backoff ** attempt)
                continue
            return {
                "ok": False,
                "error": "{}；响应开头：{}".format(last_error, body or "(空)"),
                "kind": KIND_BAD_JSON,
                "status": status,
                "attempts": attempt,
                "url": url,
            }

        return {
            "ok": True,
            "data": data,
            "status": status,
            "attempts": attempt,
            "url": url,
        }

    return {
        "ok": False,
        "error": last_error or "请求失败",
        "kind": last_kind,
        "status": last_status,
        "attempts": attempts,
        "url": url,
    }


def is_transient(kind: str) -> bool:
    """True when the failure may disappear on a later run."""
    return kind in (KIND_RATE_LIMITED, KIND_SERVER_ERROR, KIND_NETWORK, KIND_BAD_JSON)
