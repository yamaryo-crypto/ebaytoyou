"""HTTP クライアント：タイムアウト・リトライ・指数バックオフ。"""
import os
import time
from typing import Any, Optional

import requests

def get_timeout_sec() -> int:
    return int(os.getenv("HTTP_TIMEOUT_SEC", "30"))

def get_retry_max() -> int:
    return int(os.getenv("HTTP_RETRY_MAX", "3"))

def get_retry_backoff_sec() -> float:
    return float(os.getenv("HTTP_RETRY_BACKOFF_SEC", "2"))

def download_bytes(
    url: str,
    timeout_sec: Optional[int] = None,
    retry_max: Optional[int] = None,
    retry_backoff_sec: Optional[float] = None,
    session: Optional[requests.Session] = None,
) -> bytes:
    """URL からバイト列を取得。リトライ付き。"""
    timeout_sec = timeout_sec or get_timeout_sec()
    retry_max = retry_max or get_retry_max()
    retry_backoff_sec = retry_backoff_sec or get_retry_backoff_sec()
    use_session = session or requests
    last_exc: Optional[Exception] = None
    for attempt in range(retry_max + 1):
        try:
            if hasattr(use_session, "get"):
                r = use_session.get(url, timeout=timeout_sec)
            else:
                r = use_session.request("GET", url, timeout=timeout_sec)
            r.raise_for_status()
            return r.content
        except (requests.RequestException, OSError) as e:
            last_exc = e
            if attempt < retry_max:
                time.sleep(retry_backoff_sec * (2 ** attempt))
    raise last_exc  # type: ignore

def post_json(
    url: str,
    json_body: Any,
    headers: Optional[dict[str, str]] = None,
    timeout_sec: Optional[int] = None,
    session: Optional[requests.Session] = None,
) -> dict[str, Any]:
    """POST application/json。リトライは呼び出し側で行う想定。"""
    timeout_sec = timeout_sec or get_timeout_sec()
    use_session = session or requests
    h = dict(headers or {})
    if "Content-Type" not in h:
        h["Content-Type"] = "application/json"
    if hasattr(use_session, "post"):
        r = use_session.post(url, json=json_body, headers=h, timeout=timeout_sec)
    else:
        r = use_session.request("POST", url, json=json_body, headers=h, timeout=timeout_sec)
    r.raise_for_status()
    return r.json() if r.content else {}

def get_json(
    url: str,
    params: Optional[dict[str, Any]] = None,
    headers: Optional[dict[str, str]] = None,
    timeout_sec: Optional[int] = None,
    session: Optional[requests.Session] = None,
) -> dict[str, Any]:
    """GET で JSON を取得。"""
    timeout_sec = timeout_sec or get_timeout_sec()
    use_session = session or requests
    if hasattr(use_session, "get"):
        r = use_session.get(url, params=params, headers=headers or {}, timeout=timeout_sec)
    else:
        r = use_session.request("GET", url, params=params, headers=headers or {}, timeout=timeout_sec)
    r.raise_for_status()
    return r.json() if r.content else {}
