"""アカウント検証：対象アカウントが正しく検知できるかテスト。"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class VerifyResult:
    """検証結果。"""
    success: bool
    message: str
    listings_count: int = 0
    sample_item_ids: list[str] | None = None
    sample_item_urls: list[str] | None = None
    seller_matches: bool = False
    recommended_seller: str | None = None


def verify_account() -> VerifyResult:
    """
    対象アカウント（EBAY_SELLER_USERNAME）が正しく検知できるか検証。
    filter=sellers:{seller_username} でセラーID指定。ストアURLは使用しない。
    EBAY_USER_REFRESH_TOKEN があれば Trading API で高速取得。なければ Browse API で検索。
    """
    seller_username = os.getenv("EBAY_SELLER_USERNAME", "").strip()
    if not seller_username:
        return VerifyResult(
            success=False,
            message="EBAY_SELLER_USERNAME が設定されていません。設定ページで入力してください。",
        )

    best_listings: list = []
    seller_names = [seller_username]

    # EBAY_USER_REFRESH_TOKEN があれば Trading API を優先（全サイトから一括取得）
    from app.ebay.user_token import get_user_access_token, has_user_refresh_token
    if has_user_refresh_token():
        try:
            from app.ebay.trading import get_my_ebay_selling_active
            user_token = get_user_access_token()
            if user_token:
                best_listings = get_my_ebay_selling_active(
                    user_token, seller_username, max_total=1000
                )
        except Exception as e:
            logger.warning("アカウント検証: Trading API 失敗、Browse API でフォールバック: %s", e)

    # Trading API で取れなかった場合のみ Browse API で検索
    # 日本からのアクセスでは1マーケットだと少数しか返らないため、複数マーケットを試してマージ
    seen_ids: set[str] = set()
    if not best_listings:
        try:
            from app.ebay import auth, browse, api_client as ebay_api
        except Exception as e:
            return VerifyResult(
                success=False,
                message=f"モジュール読み込みエラー: {e}",
            )

        try:
            auth.get_access_token()
        except Exception as e:
            return VerifyResult(
                success=False,
                message=f"eBay API 認証エラー: {e}",
            )

        for mpid in ebay_api.FALLBACK_MARKETPLACES:
            try:
                items = browse.search_all_my_fixed_price_listings(
                    seller_username,
                    max_total=1000,
                    sort="newlyListed",
                    marketplace_id=mpid,
                )
                for s in items:
                    if s.item_id not in seen_ids and s.is_from_any_seller(seller_names):
                        seen_ids.add(s.item_id)
                        best_listings.append(s)
            except Exception:
                pass
            if len(best_listings) >= 1000:
                break

    if not best_listings:
        try:
            from app.ebay import browse, api_client as ebay_api
            resp = browse.search_my_fixed_price_listings(
                seller_username,
                limit=50,
                offset=0,
                sort="newlyListed",
                marketplace_id=ebay_api.get_marketplace_id(),
            )
            best_listings = [s for s in resp.item_summaries if s.is_from_any_seller(seller_names)]
        except Exception as e:
            return VerifyResult(
                success=False,
                message=f"出品検索エラー: {e}",
            )

    my_listings = best_listings
    total = len(my_listings)
    # 有効な item_id を持つ出品だけをサンプルに（0 や空は除外）
    def _numeric_item_id(item_id: str) -> str:
        if not item_id or item_id.strip() == "0":
            return ""
        if "|" in item_id:
            parts = item_id.split("|")
            # v1|123456789|0 形式のときは中央が数値ID
            if len(parts) >= 2 and parts[1].strip().isdigit():
                return parts[1].strip()
            if parts[0].strip().isdigit():
                return parts[0].strip()
        return item_id.strip() if item_id.strip().isdigit() else ""

    valid_sample = [s for s in my_listings[:20] if _numeric_item_id(s.item_id)]
    sample_items = valid_sample[:5]
    sample_ids = [s.item_id for s in sample_items]
    sample_urls = []
    for s in sample_items:
        num_id = _numeric_item_id(s.item_id)
        if s.item_web_url and "/itm/" in s.item_web_url and num_id:
            sample_urls.append(s.item_web_url)
        elif num_id:
            sample_urls.append(f"https://www.ebay.com/itm/{num_id}")
        else:
            sample_urls.append(f"https://www.ebay.com/itm/{s.item_id}")

    if total == 0:
        return VerifyResult(
            success=False,
            message=f"出品が0件です。ユーザー名 '{seller_username}' が正しいか、"
            "EBAY_MARKETPLACE_ID がアカウントのサイトと一致しているか確認してください。",
            listings_count=0,
        )

    return VerifyResult(
        success=True,
        message=f"✅ 対象アカウント '{seller_username}' を正しく検知できました。{total} 件の出品を取得しました。",
        listings_count=total,
        sample_item_ids=sample_ids,
        sample_item_urls=sample_urls,
        seller_matches=True,
    )
