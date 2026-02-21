"""
対象出品の選定ロジック。
Trading API を優先（EBAY_USER_REFRESH_TOKEN 設定時）。失敗時のみ Browse API をフォールバックとして使用。
"""
from __future__ import annotations

import logging
import sqlite3
from typing import Optional, Tuple

from app.ebay import api_client, browse, models
from app.ebay.user_token import get_user_access_token, has_user_refresh_token
from app.ebay.trading import get_my_ebay_selling_active
from app.job.params import RunParams
from app.store import repo

# サブマーケットプレイスも常に試す（US で取れても IT/GB 等に追加出品がある場合をカバー）
USE_FALLBACK_MARKETPLACES_ALWAYS = True

logger = logging.getLogger(__name__)


def select_listings(
    conn: sqlite3.Connection,
    params: RunParams,
    seller_username: str,
    only_item: Optional[str],
    from_beginning: bool = False,
) -> Tuple[list[Tuple[str, Optional[str]]], dict[str, models.ItemSummary], list[str]]:
    """
    対象出品一覧と ItemSummary マップを取得。
    Trading API 優先: EBAY_USER_REFRESH_TOKEN が設定されていれば Trading API のみ使用。
    Browse API は Trading API が失敗した場合のみフォールバックとして使用。
    from_beginning=True: API順（新着順）の先頭から。24時間以上経過時など。
    from_beginning=False: 未スキャン・最も古くスキャンした順（続きから）。
    """
    if only_item:
        selected = [(only_item, None)]
        summary_map = {}
        return selected, summary_map, [seller_username]

    seller_names = [seller_username]
    # max_total: APIから取得する最大件数。search_limitとmax_listingsの大きい方を使用
    # ただし、処理する件数（max_listings）を超えて取得する必要はないので、max_listingsを優先
    max_total = max(params.max_listings, params.search_limit)
    logger.info("出品取得開始: seller=%s, max_total=%d (max_listings=%d, search_limit=%d)", 
                seller_username, max_total, params.max_listings, params.search_limit)
    seen_ids: set[str] = set()
    best_listings: list[models.ItemSummary] = []
    primary_marketplace = api_client.get_marketplace_id()

    # Trading API を優先（EBAY_USER_REFRESH_TOKEN が設定されていれば Trading API のみ使用）
    trading_api_success = False
    if has_user_refresh_token():
        try:
            user_token = get_user_access_token()
            if user_token:
                items = get_my_ebay_selling_active(user_token, seller_username, max_total=max_total)
                added = 0
                for s in items:
                    if s.item_id not in seen_ids and s.is_from_any_seller(seller_names):
                        seen_ids.add(s.item_id)
                        best_listings.append(s)
                        added += 1
                logger.info("Trading API 結果: 取得=%d件, マージ追加=%d件, 合計=%d件", len(items), added, len(best_listings))
                if len(items) > 0:
                    trading_api_success = True
                    logger.info("Trading API で出品取得成功。Browse API はスキップします（Trading API 優先運用）")
        except Exception as e:
            logger.warning("Trading API 取得失敗: %s。Browse API をフォールバックとして使用します", e)

    # Browse API は Trading API が失敗した場合のみフォールバックとして使用
    if not trading_api_success:
        logger.info("Browse API で検索（Trading API が利用できないためフォールバック）")
        # 1) Browse API で検索（filter=sellers:{seller_username} でセラーID指定）
        try:
            items = browse.search_all_my_fixed_price_listings(
                seller_username,
                max_total=max_total,
                sort=params.search_sort,
                additional_sellers=None,
                marketplace_id=primary_marketplace,
            )
            added = 0
            for s in items:
                if s.item_id not in seen_ids and s.is_from_any_seller(seller_names):
                    seen_ids.add(s.item_id)
                    best_listings.append(s)
                    added += 1
            logger.info(
                "Browse API: seller=%s, マーケット=%s, 取得=%d件, マージ追加=%d件, 合計=%d件",
                seller_username, primary_marketplace, len(items), added, len(best_listings),
            )
        except Exception as e:
            logger.warning("Browse API 取得失敗: seller=%s, マーケット=%s, エラー=%s", seller_username, primary_marketplace, e)

        # 2) サブサイト（IT/GB/DE/FR/AU等）も試してマージ（Browse API 使用時のみ）
        if USE_FALLBACK_MARKETPLACES_ALWAYS:
            for mpid in api_client.FALLBACK_MARKETPLACES:
                if mpid == primary_marketplace:
                    continue
                try:
                    items = browse.search_all_my_fixed_price_listings(
                        seller_username,
                        max_total=max_total,
                        sort=params.search_sort,
                        additional_sellers=None,
                        marketplace_id=mpid,
                    )
                    added = 0
                    for s in items:
                        if s.item_id not in seen_ids and s.is_from_any_seller(seller_names):
                            seen_ids.add(s.item_id)
                            best_listings.append(s)
                            added += 1
                    if added > 0 or len(items) > 0:
                        logger.info(
                            "Browse API (サブ): seller=%s, マーケット=%s, 取得=%d件, マージ追加=%d件, 合計=%d件",
                            seller_username, mpid, len(items), added, len(best_listings),
                        )
                except Exception as e:
                    logger.warning("Browse API (サブ) 取得失敗: seller=%s, マーケット=%s, エラー=%s", seller_username, mpid, e)
                if len(best_listings) >= max_total:
                    break

        if not best_listings:
            try:
                items = browse.search_all_my_fixed_price_listings(
                    seller_username,
                    max_total=max_total,
                    sort=params.search_sort,
                    marketplace_id=primary_marketplace,
                )
                best_listings = [s for s in items if s.is_from_any_seller(seller_names)]
                logger.info("Browse API (フォールバック): 取得=%d件, セラー一致=%d件", len(items), len(best_listings))
            except Exception as e:
                logger.warning("Browse API (フォールバック) 取得失敗: %s", e)
    else:
        logger.info("Trading API 優先運用: Browse API は実行しません")

    all_listing_ids = [s.item_id for s in best_listings]
    logger.info(
        "出品取得完了: 実際にリストに格納した数=%d件, 今回の処理対象=%d件 (from_beginning=%s)",
        len(all_listing_ids), min(len(all_listing_ids), params.max_listings), from_beginning,
    )
    summary_map = {s.item_id: s for s in best_listings}

    if from_beginning:
        selected = [(lid, None) for lid in all_listing_ids[: params.max_listings]]
    else:
        selected = repo.get_listings_scan_state_for_selection(
            conn, params.max_listings, all_listing_ids
        )
    return selected, summary_map, seller_names


def compute_listing_status(
    listing_errors: int,
    image_urls: list[str],
) -> str:
    """1出品のスキャン結果ステータスを返す。"""
    if listing_errors == len(image_urls):
        return "fail"
    return "partial" if listing_errors else "success"



