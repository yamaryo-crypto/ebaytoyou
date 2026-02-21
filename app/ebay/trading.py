"""Trading API: GetMyeBaySelling（自分の出品一覧取得）。User OAuth 必須。"""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import Optional

import requests
from dotenv import load_dotenv

from app.ebay import models
from app.util import http

load_dotenv()

logger = logging.getLogger(__name__)

TRADING_ENDPOINT = "https://api.ebay.com/ws/api.dll"
API_VERSION = "1451"

# SiteID → マーケットプレイス名（ログ用）
SITE_ID_TO_NAME: dict[int, str] = {
    0: "US",
    3: "UK",
    15: "AU",
    77: "DE",
    101: "IT",
    71: "FR",
}

# paginationInput: Trading API の EntriesPerPage 最大値（GetMyeBaySelling は 200 まで可）
PAGINATION_ENTRIES_PER_PAGE = 200

# マーケットプレイスID → Trading API SiteID（複数サイトで取得して400件超に対応）
# US=0, UK=3, AU=15, DE=77, IT=101, FR=71
MARKETPLACE_TO_SITE_ID: dict[str, int] = {
    "EBAY_US": 0,
    "EBAY_UK": 3,
    "EBAY_GB": 3,
    "EBAY_AU": 15,
    "EBAY_DE": 77,
    "EBAY_IT": 101,
    "EBAY_FR": 71,
}


def _build_get_my_ebay_selling_xml(
    page: int = 1, entries_per_page: int = 100, include_listing_type: bool = False
) -> str:
    """
    GetMyeBaySelling リクエスト XML。
    paginationInput: EntriesPerPage（100=最大値）, PageNumber で全件取得。
    """
    listing_line = "    <ListingType>FixedPriceItem</ListingType>\n" if include_listing_type else ""
    return f"""<?xml version="1.0" encoding="utf-8"?>
<GetMyeBaySellingRequest xmlns="urn:ebay:apis:eBLBaseComponents">
  <RequesterCredentials>
    <eBayAuthToken>{{token}}</eBayAuthToken>
  </RequesterCredentials>
  <DetailLevel>ReturnAll</DetailLevel>
  <ActiveList>
    <Include>true</Include>
{listing_line}    <Pagination>
      <EntriesPerPage>{entries_per_page}</EntriesPerPage>
      <PageNumber>{page}</PageNumber>
    </Pagination>
  </ActiveList>
</GetMyeBaySellingRequest>"""


def _parse_item(element: ET.Element, seller_username: str) -> Optional[models.ItemSummary]:
    """Trading API Item 要素を ItemSummary に変換。"""
    item_id_el = element.find(".//{urn:ebay:apis:eBLBaseComponents}ItemID")
    view_url_el = element.find(".//{urn:ebay:apis:eBLBaseComponents}ViewItemURL")
    if item_id_el is None or item_id_el.text is None:
        return None
    item_id = item_id_el.text.strip()
    item_web_url = (view_url_el.text or "").strip() or f"https://www.ebay.com/itm/{item_id}"

    title_el = element.find(".//{urn:ebay:apis:eBLBaseComponents}Title")
    title = (title_el.text or "").strip() or None

    # 画像URL
    pic_urls = []
    pic_details = element.find(".//{urn:ebay:apis:eBLBaseComponents}PictureDetails")
    if pic_details is not None:
        for pic in pic_details.findall(".//{urn:ebay:apis:eBLBaseComponents}PictureURL"):
            if pic.text and pic.text.strip():
                pic_urls.append(pic.text.strip())

    if not pic_urls:
        return None

    img = models.ImageInfo(image_url=pic_urls[0])
    addl = [models.ImageInfo(image_url=u) for u in pic_urls[1:]]
    seller = models.Seller(username=seller_username, user_id=seller_username)
    return models.ItemSummary(
        item_id=item_id,
        item_web_url=item_web_url,
        image=img,
        additional_images=addl,
        seller=seller,
        title=title,
    )


def _fetch_my_ebay_selling_one_site(
    user_token: str,
    seller_username: str,
    site_id: int,
    max_total: int,
) -> list[models.ItemSummary]:
    """
    1サイト分の GetMyeBaySelling を実行。
    paginationInput: EntriesPerPage=200（最大値）, PageNumber をインクリメントして全件取得。
    """
    all_items: list[models.ItemSummary] = []
    page_number = 1
    entries_per_page = PAGINATION_ENTRIES_PER_PAGE
    total_from_api: Optional[int] = None

    while len(all_items) < max_total:
        body = _build_get_my_ebay_selling_xml(page_number, entries_per_page, include_listing_type=False).replace("{token}", user_token)
        print(
            f"[DEBUG] Trading API リクエスト: {TRADING_ENDPOINT} "
            f"(EntriesPerPage={entries_per_page}, PageNumber={page_number})"
        )
        if page_number == 1:
            # リクエストXMLをログに出力（トークンはマスク）
            body_masked = body.replace(user_token, "***TOKEN_MASKED***")
            print(f"[DEBUG] Trading API リクエストXML:")
            print(body_masked)
        logger.info(
            "Trading API GetMyeBaySelling: ページ%d (EntriesPerPage=%d) 取得中...",
            page_number, entries_per_page,
        )
        r = requests.post(
            TRADING_ENDPOINT,
            headers={
                "X-EBAY-API-COMPATIBILITY-LEVEL": API_VERSION,
                "X-EBAY-API-CALL-NAME": "GetMyeBaySelling",
                "X-EBAY-API-SITEID": str(site_id),
                "Content-Type": "text/xml",
            },
            data=body.encode("utf-8"),
            timeout=http.get_timeout_sec(),
        )
        r.raise_for_status()
        root = ET.fromstring(r.content)

        # エラーチェック
        ack = root.find(".//{urn:ebay:apis:eBLBaseComponents}Ack")
        if ack is not None and ack.text and ack.text in ("Failure", "PartialFailure"):
            err = root.find(".//{urn:ebay:apis:eBLBaseComponents}ShortMessage")
            msg = err.text if err is not None else "Unknown error"
            raise RuntimeError(f"GetMyeBaySelling error: {msg}")

        active_list = root.find(".//{urn:ebay:apis:eBLBaseComponents}ActiveList")
        if active_list is None:
            # ActiveListが存在しない = そのサイトに出品がない
            logger.info("Trading API: ActiveList が見つかりません (SiteID=%d) - このサイトには出品がない可能性があります", site_id)
            print(f"[DEBUG] Trading API: ActiveList が見つかりません (SiteID={site_id}) - このサイトには出品がない可能性があります")
            # XMLレスポンス全体をログに出力（デバッグ用）
            xml_str = ET.tostring(root, encoding='unicode')
            print(f"[DEBUG] Trading API XMLレスポンス全体:")
            print(xml_str)
            # このサイトには出品がないので、次のサイトに進む
            break

        # PaginationResult から総ヒット数を取得
        pagination_result = active_list.find(".//{urn:ebay:apis:eBLBaseComponents}PaginationResult")
        if pagination_result is not None:
            total_el = pagination_result.find(".//{urn:ebay:apis:eBLBaseComponents}TotalNumberOfEntries")
            if total_el is not None and total_el.text:
                total_from_api = int(total_el.text)
                if page_number == 1:
                    logger.info("Trading API GetMyeBaySelling: TotalNumberOfEntries（総ヒット数）=%d", total_from_api)
                    print(f"[DEBUG] Trading API: SiteID {site_id} 総ヒット数={total_from_api}件")
            else:
                if page_number == 1:
                    print(f"[DEBUG] Trading API: SiteID {site_id} TotalNumberOfEntries が見つかりません")

        items = active_list.findall(".//{urn:ebay:apis:eBLBaseComponents}Item")
        if page_number == 1 and len(items) == 0:
            # アイテムが0件の場合、レスポンスの構造を確認
            print(f"[DEBUG] Trading API: SiteID {site_id} でItem要素が0件です。ActiveListの構造を確認:")
            active_list_str = ET.tostring(active_list, encoding='unicode')[:1000]
            print(f"[DEBUG] Trading API ActiveList XML（最初の1000文字）: {active_list_str}")
        for item_el in items:
            parsed = _parse_item(item_el, seller_username)
            if parsed:
                all_items.append(parsed)

        logger.info(
            "Trading API GetMyeBaySelling: ページ%d 取得完了 取得=%d件, 累計=%d件",
            page_number, len(items), len(all_items),
        )
        print(f"[DEBUG] Trading API: ページ{page_number} 取得完了 取得={len(items)}件, 累計={len(all_items)}件 (総ヒット数={total_from_api if total_from_api is not None else 'N/A'})")
        # 総件数まで取得済みなら終了
        if total_from_api is not None and len(all_items) >= min(max_total, total_from_api):
            print(f"[DEBUG] Trading API: 総件数に達したため終了 (累計={len(all_items)}, 総ヒット数={total_from_api})")
            break
        # 返却件数が EntriesPerPage 未満なら通常は最終ページ。
        # ただし TotalNumberOfEntries がそれより大きい場合は次ページを試す（APIが40件ずつ返す等の対策）。
        if len(items) < entries_per_page:
            if total_from_api is None or len(all_items) >= min(max_total, total_from_api):
                print(f"[DEBUG] Trading API: 最終ページのため終了 (取得={len(items)}件 < EntriesPerPage={entries_per_page})")
                break
        print(f"[DEBUG] Trading API: 次ページへ進みます (ページ{page_number} → {page_number + 1})")
        page_number += 1

    result = all_items[:max_total]
    logger.info(
        "Trading API GetMyeBaySelling (SiteID=%d): 総ヒット数（TotalNumberOfEntries）=%s, 実際にリストに格納した数=%d",
        site_id, str(total_from_api) if total_from_api is not None else "N/A", len(result),
    )
    return result


def get_my_ebay_selling_active(
    user_token: str,
    seller_username: str,
    max_total: int = 1000,
) -> list[models.ItemSummary]:
    """
    GetMyeBaySelling で出品中一覧を取得。
    複数サイト（US/UK/AU/DE/IT/FR）を順に取得してマージ。400件超に対応。
    User OAuth トークンが必要。
    """
    seen_ids: set[str] = set()
    all_items: list[models.ItemSummary] = []
    site_ids = [0, 3, 15, 77, 101, 71]  # US, UK, AU, DE, IT, FR

    for site_id in site_ids:
        if len(all_items) >= max_total:
            break
        site_name = SITE_ID_TO_NAME.get(site_id, str(site_id))
        try:
            items = _fetch_my_ebay_selling_one_site(
                user_token, seller_username, site_id, max_total=max_total
            )
            new_count = sum(1 for s in items if s.item_id not in seen_ids)
            for s in items:
                if s.item_id not in seen_ids:
                    seen_ids.add(s.item_id)
                    all_items.append(s)
            logger.info(
                "Trading API GetMyeBaySelling: SiteID %s (%s) 取得件数=%d (新規=%d)",
                site_id, site_name, len(items), new_count,
            )
            print(f"[DEBUG] Trading API: SiteID {site_id} ({site_name}) 取得={len(items)}件, 累計={len(all_items)}件")
        except Exception as e:
            logger.warning(
                "Trading API GetMyeBaySelling: SiteID %s (%s) 失敗: %s",
                site_id, site_name, e,
            )
            print(f"[DEBUG] Trading API: SiteID {site_id} ({site_name}) 失敗: {e}")
            continue

    result = all_items[:max_total]
    logger.info(
        "Trading API GetMyeBaySelling 完了: 実際にリストに格納した数=%d (max_total=%d)",
        len(result), max_total,
    )
    print(f"[DEBUG] Trading API 完了: 実際にリストに格納した数={len(result)}件 (max_total={max_total})")
    return result
