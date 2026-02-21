"""画像一致判定: SHA-256 / URL / perceptual hash（pHash + aHash）。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from app.match import hashing


@dataclass
class MatchResult:
    match: bool
    evidence: str  # "sha256" | "url" | "both" | "phash" | "ahash" | "dhash"


def check_match(
    our_sha256: str,
    their_sha256: str,
    our_image_url: Optional[str] = None,
    their_image_url: Optional[str] = None,
    also_accept_same_image_url: bool = False,
    our_phash: Any = None,
    their_phash: Any = None,
    our_ahash: Any = None,
    their_ahash: Any = None,
    our_dhash: Any = None,
    their_dhash: Any = None,
    phash_threshold: int = 20,
    ahash_threshold: int = 15,
    dhash_threshold: int = 22,
) -> MatchResult:
    """
    SHA-256 が一致すれば match=True, evidence="sha256"（または "both"）。
    also_accept_same_image_url が True のとき、URL が同一でも一致とみなす。
    SHA-256/URL が一致しない場合、pHash または aHash が類似していれば match=True。
    （再アップロード・再エンコード・リサイズなどでバイトが変わっても検知可能）
    """
    sha_match = bool(our_sha256 and their_sha256 and our_sha256 == their_sha256)
    url_match = False
    if also_accept_same_image_url and our_image_url and their_image_url:
        url_match = our_image_url.strip() == their_image_url.strip()
    perc_match, perc_evidence = hashing.perceptual_match(
        our_phash, their_phash, our_ahash, their_ahash,
        our_dhash=our_dhash,
        their_dhash=their_dhash,
        phash_threshold=phash_threshold,
        ahash_threshold=ahash_threshold,
        dhash_threshold=dhash_threshold,
    )

    if sha_match and url_match:
        return MatchResult(match=True, evidence="both")
    if sha_match:
        return MatchResult(match=True, evidence="sha256")
    if url_match:
        return MatchResult(match=True, evidence="url")
    if perc_match:
        return MatchResult(match=True, evidence=perc_evidence)
    return MatchResult(match=False, evidence="")
