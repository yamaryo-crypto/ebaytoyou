"""User OAuth トークン（Refresh Token から Access Token 取得）。"""
from __future__ import annotations

import base64
import os
import time
from typing import Optional

import requests
from dotenv import load_dotenv

from app.util import http

load_dotenv()

TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
# Browse + Trading API scope
# sell.inventory.readonly と sell.inventory の両方を要求
SCOPE = "https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/sell.inventory.readonly https://api.ebay.com/oauth/api_scope/sell.inventory"

_cached_user_token: Optional[str] = None
_cached_expires_at: float = 0
_BUFFER_SEC = 60


def _get_client_credentials() -> tuple[str, str]:
    cid = os.getenv("EBAY_CLIENT_ID")
    secret = os.getenv("EBAY_CLIENT_SECRET")
    if not cid or not secret:
        raise ValueError("EBAY_CLIENT_ID and EBAY_CLIENT_SECRET must be set")
    return cid, secret


def has_user_refresh_token() -> bool:
    """EBAY_USER_REFRESH_TOKEN が設定されているか。"""
    token = (os.getenv("EBAY_USER_REFRESH_TOKEN") or "").strip()
    return bool(token)


def get_user_access_token(use_cache: bool = True) -> Optional[str]:
    """
    Refresh Token から User Access Token を取得。
    EBAY_USER_REFRESH_TOKEN が未設定なら None。
    """
    global _cached_user_token, _cached_expires_at
    refresh_token = (os.getenv("EBAY_USER_REFRESH_TOKEN") or "").strip()
    if not refresh_token:
        return None

    if use_cache and _cached_user_token and time.time() < _cached_expires_at - _BUFFER_SEC:
        return _cached_user_token

    cid, secret = _get_client_credentials()
    auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    r = requests.post(
        TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Authorization": f"Basic {auth}"},
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "scope": SCOPE,
        },
        timeout=http.get_timeout_sec(),
    )
    if r.status_code != 200:
        error_msg = f"HTTP {r.status_code}: {r.text}"
        try:
            error_data = r.json()
            if "error_description" in error_data:
                error_msg += f" - {error_data['error_description']}"
        except:
            pass
        raise ValueError(f"Failed to get access token: {error_msg}")
    r.raise_for_status()
    data = r.json()
    token = data.get("access_token")
    if not token:
        raise ValueError("No access_token in response")
    expires_in = int(data.get("expires_in", 7200))
    _cached_user_token = token
    _cached_expires_at = time.time() + expires_in
    return token
