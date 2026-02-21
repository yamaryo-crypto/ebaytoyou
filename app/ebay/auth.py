"""eBay OAuth2 Client Credentials（Application access token）とキャッシュ。"""
from __future__ import annotations

import base64
import os
import time
from typing import Optional

import requests
from dotenv import load_dotenv

from app.util import http

load_dotenv()

# 本番
TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
# Browse API scope
SCOPE = "https://api.ebay.com/oauth/api_scope"

_cached_token: Optional[str] = None
_cached_expires_at: float = 0
_BUFFER_SEC = 60


def _get_client_credentials() -> tuple[str, str]:
    cid = os.getenv("EBAY_CLIENT_ID")
    secret = os.getenv("EBAY_CLIENT_SECRET")
    if not cid or not secret:
        raise ValueError("EBAY_CLIENT_ID and EBAY_CLIENT_SECRET must be set")
    return cid, secret


def get_access_token(use_cache: bool = True) -> str:
    """Application access token を返す。キャッシュがあれば有効期限まで再利用。"""
    global _cached_token, _cached_expires_at
    if use_cache and _cached_token and time.time() < _cached_expires_at - _BUFFER_SEC:
        return _cached_token
    cid, secret = _get_client_credentials()
    auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    r = requests.post(
        TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Authorization": f"Basic {auth}"},
        data={"grant_type": "client_credentials", "scope": SCOPE},
        timeout=http.get_timeout_sec(),
    )
    r.raise_for_status()
    data = r.json()
    _cached_token = data.get("access_token")
    if not _cached_token:
        raise ValueError("No access_token in response")
    expires_in = int(data.get("expires_in", 7200))
    _cached_expires_at = time.time() + expires_in
    return _cached_token
