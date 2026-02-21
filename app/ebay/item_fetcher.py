"""eBay 出品の取得（検索・直接取得）。"""
from __future__ import annotations

from typing import Optional

import requests

from app.ebay import browse, models
from app.ebay.api_client import BASE_URL, build_headers
from app.util import http


def fetch_item_by_id(
    item_id: str,
    token: str,
    search_limit: int,
    search_sort: str,
    seller_username: str,
) -> Optional[models.ItemSummary]:
    """
    出品を取得。検索結果を優先し、なければ直接取得。
    レガシーID（数値）の場合は get_item_by_legacy_id を使用。
    """
    item_id_clean = (item_id or "").strip()

    # 1) 検索結果から取得を試行（エラー時はスキップして直接取得へ）
    try:
        resp = browse.search_my_fixed_price_listings(
            seller_username, limit=search_limit, offset=0, sort=search_sort
        )
        for s in resp.item_summaries:
            if s.item_id == item_id_clean:
                return s
            # v1|xxx|0 形式とレガシーIDの両方でマッチさせる
            if "|" in s.item_id and s.item_id.split("|")[1] == item_id_clean:
                return s
    except Exception:
        pass

    # 2) 直接取得: レガシーID（数値のみ）は get_item_by_legacy_id を使用
    headers = build_headers(token)
    if item_id_clean.isdigit():
        url = f"{BASE_URL}/item/get_item_by_legacy_id"
        r = requests.get(
            url,
            params={"legacy_item_id": item_id_clean},
            headers=headers,
            timeout=http.get_timeout_sec(),
        )
    else:
        r = requests.get(
            f"{BASE_URL}/item/{item_id_clean}",
            headers=headers,
            timeout=http.get_timeout_sec(),
        )
    if r.ok:
        return models.ItemSummary.from_api(r.json())
    return None


def fetch_any_item_by_id(item_id: str, token: str) -> Optional[models.ItemSummary]:
    """
    任意の出品を ID で直接取得。自アカウント以外も取得可能。
    疑わしいアイテムの画像比較用。
    """
    item_id_clean = (item_id or "").strip()
    if not item_id_clean:
        return None
    # v1|xxx|0 形式の場合は中央の数値を使う
    legacy_id = item_id_clean
    if "|" in item_id_clean:
        parts = item_id_clean.split("|")
        if len(parts) >= 2 and parts[1].strip().isdigit():
            legacy_id = parts[1].strip()
    headers = build_headers(token)
    if legacy_id.isdigit():
        url = f"{BASE_URL}/item/get_item_by_legacy_id"
        r = requests.get(
            url,
            params={"legacy_item_id": legacy_id},
            headers=headers,
            timeout=http.get_timeout_sec(),
        )
    else:
        r = requests.get(
            f"{BASE_URL}/item/{legacy_id}",
            headers=headers,
            timeout=http.get_timeout_sec(),
        )
    if r.ok:
        return models.ItemSummary.from_api(r.json())
    return None
