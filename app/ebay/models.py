"""eBay API のレスポンス用モデル（簡易 dataclass）。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Seller:
    username: Optional[str]
    user_id: Optional[str]  # 不変ID。username が空のときに表示用に使う

    @classmethod
    def from_api(cls, d: Optional[dict[str, Any]]) -> Optional[Seller]:
        if not d:
            return None
        return cls(
            username=d.get("username"),
            user_id=d.get("userId"),
        )

    def display_name(self) -> str:
        """infringing_seller_display 用。username が無ければ user_id。"""
        if self.username:
            return self.username
        if self.user_id:
            return str(self.user_id)
        return ""

    def matches_username(self, expected: str) -> bool:
        """期待するユーザー名（username または user_id）と一致するか。大文字小文字は無視。"""
        if not expected or not expected.strip():
            return False
        exp = expected.strip().lower()
        if self.username and self.username.strip().lower() == exp:
            return True
        if self.user_id and str(self.user_id).strip().lower() == exp:
            return True
        return False


@dataclass
class ImageInfo:
    image_url: str

    @classmethod
    def from_api(cls, d: Optional[dict[str, Any]]) -> Optional[ImageInfo]:
        if not d:
            return None
        url = d.get("imageUrl")
        if not url:
            return None
        return cls(image_url=url)


@dataclass
class ItemSummary:
    item_id: str
    item_web_url: str
    image: Optional[ImageInfo]
    additional_images: list[ImageInfo]
    seller: Optional[Seller]
    title: Optional[str] = None

    @classmethod
    def from_api(cls, d: dict[str, Any]) -> ItemSummary:
        img = ImageInfo.from_api(d.get("image"))
        addl = [ImageInfo.from_api(x) for x in (d.get("additionalImages") or []) if ImageInfo.from_api(x)]
        title = (d.get("title") or "").strip() or None
        return cls(
            item_id=str(d.get("itemId", "")),
            item_web_url=d.get("itemWebUrl", ""),
            image=img,
            additional_images=addl,
            seller=Seller.from_api(d.get("seller")),
            title=title if title else None,
        )

    def is_from_seller(self, seller_username: str) -> bool:
        """この出品が指定セラー（EBAY_SELLER_USERNAME）のものかどうか。"""
        if not self.seller:
            return False
        return self.seller.matches_username(seller_username)

    def is_from_any_seller(self, seller_names: list[str]) -> bool:
        """指定のいずれかのセラー名と一致するか。"""
        if not self.seller or not seller_names:
            return False
        return any(self.seller.matches_username(n) for n in seller_names)

    def image_urls(self, max_count: int = 3) -> list[str]:
        """主画像 + 追加画像を先頭から max_count 枚。"""
        urls: list[str] = []
        if self.image and self.image.image_url:
            urls.append(self.image.image_url)
        for a in self.additional_images:
            if len(urls) >= max_count:
                break
            if a.image_url:
                urls.append(a.image_url)
        return urls[:max_count]


@dataclass
class SearchResponse:
    item_summaries: list[ItemSummary]
    total: int
    offset: int
    limit: int
    next_url: Optional[str] = None  # 次ページのURI（eBay推奨のページネーション用）

    @classmethod
    def from_api(cls, d: dict[str, Any]) -> SearchResponse:
        items = [ItemSummary.from_api(x) for x in (d.get("itemSummaries") or [])]
        next_url = d.get("next")
        if isinstance(next_url, str) and next_url.strip():
            next_url = next_url.strip()
        else:
            next_url = None
        return cls(
            item_summaries=items,
            total=int(d.get("total", 0) or 0),
            offset=int(d.get("offset", 0) or 0),
            limit=int(d.get("limit", 0) or 0),
            next_url=next_url,
        )
