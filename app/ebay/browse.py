"""eBay Browse API: item_summary/search, item_summary/search_by_image。"""
from __future__ import annotations

import logging
import os
from typing import Optional
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

from app.ebay import auth, models
from app.ebay.api_client import BASE_URL, build_headers, get_delivery_country, use_delivery_country_filter
from app.util import http

load_dotenv()
logger = logging.getLogger(__name__)

# Browse API item_summary/search の limit 最大値（API仕様上必ず200固定）
BROWSE_API_LIMIT = 200


def _search_query() -> str:
    """
    検索キーワード。sellers フィルタと併用。環境変数 EBAY_SEARCH_QUERY で上書き可能。
    デフォルトは空文字列（sellers フィルタのみで検索。ただし、eBay APIが空文字列を許可しない場合は最小限の値を使用）。
    注意: q パラメータは必須だが、sellers フィルタがある場合でも、q の値が結果に影響する可能性がある。
    "a" だと「a」というキーワードで検索してしまい、結果が制限される可能性があるため、
    より一般的なキーワードや、空文字列に近い値を試す。
    """
    query = (os.getenv("EBAY_SEARCH_QUERY") or "").strip()
    # 環境変数が設定されていない場合、空文字列を返す（APIが許可しない場合は呼び出し側で処理）
    # 以前は "a" を使用していたが、これが結果を制限していた可能性がある
    return query


def _build_filter(seller_username: str, additional_sellers: Optional[list[str]] = None, marketplace_id: Optional[str] = None) -> str:
    """filter クエリパラメータを構築。sellers と buyingOptions を必ず含む。deliveryCountry は環境変数で制御可能。"""
    sellers = [s for s in [seller_username] + (additional_sellers or []) if s]
    sellers_str = "|".join(sellers) if len(sellers) > 1 else sellers[0]
    filter_parts = [f"sellers:{{{sellers_str}}}", "buyingOptions:{FIXED_PRICE|BEST_OFFER}"]
    # deliveryCountry フィルタはデフォルト無効（日本発送の出品も取得するため）
    # EBAY_USE_DELIVERY_COUNTRY=1 で有効化可能
    if use_delivery_country_filter():
        country = get_delivery_country(marketplace_id)
        filter_parts.append(f"deliveryCountry:{country}")
    return ",".join(filter_parts)


def search_my_fixed_price_listings(
    seller_username: str,
    limit: int = BROWSE_API_LIMIT,
    offset: int = 0,
    sort: Optional[str] = None,
    additional_sellers: Optional[list[str]] = None,
    marketplace_id: Optional[str] = None,
) -> models.SearchResponse:
    """
    GET item_summary/search を1回呼び出し SearchResponse を返す。
    limit は API 最大値 200 固定（超えると 400 Bad Request）。
    """
    limit = min(int(limit), BROWSE_API_LIMIT)
    filter_val = _build_filter(seller_username, additional_sellers, marketplace_id)
    search_query = _search_query()
    # q パラメータは必須。sellersフィルタがある場合でも、q の値が結果に影響する可能性がある。
    # "a" だと「a」というキーワードで検索してしまい、結果が制限される可能性がある。
    # より一般的なキーワードを使用するか、環境変数で指定された値を使用する。
    # デフォルトは空文字列だが、APIが許可しない場合は最小限の値を使用。
    if not search_query:
        # sellersフィルタがある場合、q パラメータには最小限の値を使用
        # 以前は "a" を使用していたが、これが結果を制限していた可能性がある
        # より一般的なキーワードを試す
        search_query = " "  # スペース1文字を試す（空文字列に近いが、APIが許可する可能性がある）
    params: dict[str, str | int] = {
        "q": search_query,
        "limit": limit,
        "offset": offset,
        "filter": filter_val,
    }
    if sort:
        params["sort"] = sort
    url = f"{BASE_URL}/item_summary/search"
    full_url = f"{url}?{urlencode(params)}"
    print(f"[DEBUG] Browse API リクエストURL: {full_url}")  # limit=200, filter=sellers:{...} を確認
    token = auth.get_access_token()
    r = requests.get(
        url,
        params=params,
        headers=build_headers(token, marketplace_id=marketplace_id),
        timeout=http.get_timeout_sec(),
    )
    r.raise_for_status()
    return models.SearchResponse.from_api(r.json())


def search_all_my_fixed_price_listings(
    seller_username: str,
    max_total: int = 500,
    sort: Optional[str] = None,
    additional_sellers: Optional[list[str]] = None,
    marketplace_id: Optional[str] = None,
) -> list[models.ItemSummary]:
    """
    全出品を offset ベースのページネーションで取得。
    要件:
    - limit は API 最大値 200 固定（next は使用しない）
    - offset を 0, 200, 400... と加算してループ
    - 終了条件: 取得件数が 0 または max_total に達した時
    """
    all_items: list[models.ItemSummary] = []
    offset = 0
    limit = BROWSE_API_LIMIT  # 200（API仕様上の最大値、必ず固定）

    while True:
        logger.info("Browse API: offset=%d, limit=%d で取得中... (これまでの取得総数: %d)", offset, limit, len(all_items))
        print(f"現在 {offset} 件目から {limit} 件を取得中... (これまでの取得総数: {len(all_items)})")
        try:
            resp = search_my_fixed_price_listings(
                seller_username,
                limit=limit,
                offset=offset,
                sort=sort,
                additional_sellers=additional_sellers,
                marketplace_id=marketplace_id,
            )
            items = resp.item_summaries
            n = len(items) if items else 0
            total_from_api = resp.total  # APIが返す総件数
            logger.info("Browse API: レスポンス取得成功。item_summaries=%d件, total=%d件", n, total_from_api)
            print(f"[DEBUG] Browse API レスポンス: 取得={n}件, API総件数={total_from_api}件 (マーケット={marketplace_id or 'default'})")
        except Exception as e:
            logger.error("Browse API: 取得エラー (offset=%d): %s", offset, e, exc_info=True)
            print(f"[DEBUG] Browse API エラー: {e}")
            break

        # 終了条件1: 取得できたアイテム数が 0 になった時
        if not items:
            logger.info("Browse API: 取得0件のため終了 (offset=%d)", offset)
            print(f"[DEBUG] Browse API: 取得0件のため終了 (offset={offset})")
            break

        all_items.extend(items)
        logger.info("Browse API: 追加後、累計=%d件", len(all_items))
        print(f"[DEBUG] Browse API: 追加後、累計={len(all_items)}件 (API総件数={total_from_api})")

        # 終了条件2: 設定された最大取得数に達した時
        if len(all_items) >= max_total:
            logger.info("Browse API: max_total=%d に達したため終了", max_total)
            print(f"[DEBUG] Browse API: max_total={max_total}に達したため終了")
            break

        # 終了条件3: APIの総件数まで取得済み
        if total_from_api > 0 and len(all_items) >= min(max_total, total_from_api):
            logger.info("Browse API: API総件数（%d件）まで取得済みのため終了", total_from_api)
            print(f"[DEBUG] Browse API: API総件数（{total_from_api}件）まで取得済みのため終了")
            break

        # 取得件数が limit 未満なら通常は最終ページ
        # ただし、API総件数がそれより大きい場合は次ページを試す（APIが一部しか返さない場合の対策）
        if len(items) < limit:
            if total_from_api == 0 or len(all_items) >= min(max_total, total_from_api):
                logger.info("Browse API: 最終ページ (取得=%d < limit=%d) のため終了", len(items), limit)
                print(f"[DEBUG] Browse API: 最終ページのため終了 (取得={len(items)}件 < limit={limit})")
                break
            else:
                logger.info("Browse API: 取得件数が少ないが、API総件数（%d件）が大きいため次ページを試します", total_from_api)
                print(f"[DEBUG] Browse API: 取得={len(items)}件だが、API総件数={total_from_api}件のため次ページへ")

        offset += limit

    result = all_items[:max_total]
    logger.info(
        "Browse API 完了: 実際にリストに格納した数=%d (max_total=%d)",
        len(result), max_total,
    )
    print(f"[DEBUG] Browse API 完了: 実際にリストに格納した数={len(result)}件 (max_total={max_total})")
    return result


def search_by_keywords(
    query: str,
    limit: int = BROWSE_API_LIMIT,
    offset: int = 0,
    sort: Optional[str] = "bestMatch",
    marketplace_id: Optional[str] = None,
) -> models.SearchResponse:
    """
    キーワードで検索（セラー指定なし）。
    画像検索に引っかからないリサイズ流用を検知するため、同商品を扱う他セラーの候補を取得。
    """
    query_clean = (query or "").strip()
    if not query_clean or len(query_clean) < 2:
        return models.SearchResponse(
            item_summaries=[],
            total=0,
            offset=offset,
            limit=limit,
        )
    limit = min(int(limit), BROWSE_API_LIMIT)
    country = get_delivery_country(marketplace_id)
    filter_val = f"buyingOptions:{{FIXED_PRICE|BEST_OFFER}},deliveryCountry:{country}"
    params: dict[str, str | int] = {
        "q": query_clean[:350],
        "limit": limit,
        "offset": offset,
        "filter": filter_val,
    }
    if sort:
        params["sort"] = sort
    token = auth.get_access_token()
    url = f"{BASE_URL}/item_summary/search"
    r = requests.get(
        url,
        params=params,
        headers=build_headers(token, marketplace_id=marketplace_id),
        timeout=http.get_timeout_sec(),
    )
    r.raise_for_status()
    return models.SearchResponse.from_api(r.json())


def search_by_image(
    image_base64: str,
    limit: int = 50,
    offset: int = 0,
    marketplace_id: Optional[str] = None,
) -> models.SearchResponse:
    """POST item_summary/search_by_image with body {"image": "<Base64>"}. Sandbox 非対応。"""
    token = auth.get_access_token()
    url = f"{BASE_URL}/item_summary/search_by_image"
    params = {"limit": limit, "offset": offset}
    body = {"image": image_base64}
    
    # Base64データのサイズを確認（デバッグ用）
    image_size = len(image_base64) if image_base64 else 0
    logger.debug("search_by_image: image_size=%d bytes, limit=%d", image_size, limit)
    
    try:
        r = requests.post(
            url,
            params=params,
            headers=build_headers(token, marketplace_id=marketplace_id),
            json=body,
            timeout=http.get_timeout_sec(),
        )
        r.raise_for_status()
        return models.SearchResponse.from_api(r.json() if r.content else {"itemSummaries": [], "total": 0, "offset": 0, "limit": limit})
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP {r.status_code}: {r.text[:500]}" if hasattr(e, 'response') and e.response else str(e)
        logger.error("search_by_image HTTPエラー: %s", error_msg)
        raise
    except Exception as e:
        logger.error("search_by_image エラー: %s", str(e), exc_info=True)
        raise
