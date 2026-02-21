"""eBay Browse API の共通クライアント設定。"""
from __future__ import annotations

import os

from app.constants import DEFAULT_MARKETPLACE_ID

BASE_URL = "https://api.ebay.com/buy/browse/v1"


def get_marketplace_id() -> str:
    """マーケットプレイスIDを取得。EBAY_IT=ebay.it, EBAY_US=ebay.com。"""
    return os.getenv("EBAY_MARKETPLACE_ID", DEFAULT_MARKETPLACE_ID)


# 出品が少ない場合に試す追加マーケットプレイス（US メイン、IT/AU 等はサブ）
# US を優先し、IT/GB/DE/FR/AU をサブとして試す
FALLBACK_MARKETPLACES = ["EBAY_US", "EBAY_IT", "EBAY_GB", "EBAY_DE", "EBAY_FR", "EBAY_AU"]

# マーケットプレイスID → 国コード（deliveryCountry / X-EBAY-C-ENDUSERCTX 用）
# 日本以外をデフォルト対象（外国人向け出品がほとんど）
MARKETPLACE_TO_COUNTRY: dict[str, str] = {
    "EBAY_US": "US",
    "EBAY_IT": "IT",
    "EBAY_GB": "GB",
    "EBAY_DE": "DE",
    "EBAY_FR": "FR",
    "EBAY_AU": "AU",
    "EBAY_CA": "CA",
    "EBAY_ES": "ES",
}


def get_delivery_country(marketplace_id: str | None) -> str:
    """マーケットプレイスに対応する配送先国コードを返す。デフォルトは US（日本人ではなく外国人在住地向け）。"""
    mpid = marketplace_id or get_marketplace_id()
    return MARKETPLACE_TO_COUNTRY.get(mpid, "US")


def use_delivery_country_filter() -> bool:
    """filter に deliveryCountry を付けるか。デフォルト無効（絞り込み過多で0件になるのを避ける）。"""
    v = (os.getenv("EBAY_USE_DELIVERY_COUNTRY", "0") or "").strip().lower()
    return v not in ("0", "false", "no", "off", "")


def build_headers(token: str, marketplace_id: str | None = None) -> dict[str, str]:
    """API リクエスト用ヘッダを構築。marketplace_id 指定時はそれを使用。"""
    mpid = marketplace_id or get_marketplace_id()
    country = get_delivery_country(mpid)
    headers: dict[str, str] = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": mpid,
        "Content-Type": "application/json",
    }
    # 配送先フィルタを避けるため、常に「米国在住」としてAPIに認識させる（日本からのアクセスでも全件取得するため）
    headers["X-EBAY-C-ENDUSERCTX"] = "contextualLocation=country=US,zip=10001"
    return headers
