"""
1出品あたりの処理ロジック。
画像スキャン・候補チェック・侵害検知を実行。
"""
from __future__ import annotations

import logging
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Tuple

from app.ebay import browse, item_fetcher, models
from app.job.params import RunParams
from app.match import hashing, matcher
from app.msg import generator
from app.store import repo
from app.util import http
from app.util.image import to_base64_for_search

logger = logging.getLogger(__name__)


def _download_candidate_image(url: str) -> Optional[bytes]:
    """候補画像を1件ダウンロード。失敗時は None。"""
    try:
        return http.download_bytes(url)
    except Exception:
        return None


def _collect_candidates_to_check(
    search_resp: models.SearchResponse,
    listing_item_id: str,
    seller_names: list[str],
    include_additional_images: bool = False,
) -> list[Tuple[models.ItemSummary, str]]:
    """スキップ対象を除いた候補リストを収集。自アカウント（seller_names）の出品は除外。"""
    result: list[Tuple[models.ItemSummary, str]] = []
    for candidate in search_resp.item_summaries:
        if candidate.is_from_any_seller(seller_names):
            continue
        if candidate.item_id == listing_item_id:
            continue
        urls = candidate.image_urls(12) if include_additional_images else (
            [candidate.image.image_url] if candidate.image and candidate.image.image_url else []
        )
        for url in urls:
            if url:
                result.append((candidate, url))
    return result


def _extract_search_keywords(title: Optional[str], max_chars: int = 60) -> list[str]:
    """
    タイトルから検索用キーワードを抽出。
    複数パターンを返し、広く候補を拾う（リサイズ流用検知のため）。
    """
    if not title or not title.strip():
        return []
    t = title.strip()
    words = t.split()
    if not words:
        return []
    result: list[str] = []
    # パターン1: 最初の単語群（品名・ブランド）
    kw1 = " ".join(words[:8])[:max_chars]
    if kw1.strip():
        result.append(kw1.strip())
    # パターン2: ブランド+製品タイプ（例: "Dupont Cufflinks"）で幅広く検索
    t_lower = t.lower()
    brand_combos = [
        ("dupont", "cufflinks"), ("dupont", "tie clip"), ("dupont", "ring"),
        ("cartier", "cufflinks"), ("tiffany", "ring"), ("gucci", "bracelet"),
    ]
    for brand, product in brand_combos:
        if brand in t_lower and product in t_lower:
            combo = f"{brand.title()} {product.title()}"
            if combo not in result:
                result.append(combo)
            break
    return result


def _collect_keyword_candidates(
    title: Optional[str],
    listing_item_id: str,
    seller_names: list[str],
    limit: int,
) -> list[Tuple[models.ItemSummary, str]]:
    """
    タイトルでキーワード検索し、他セラーの候補を取得。
    画像検索に引っかからないリサイズ流用を一括スキャンで検知するため。
    """
    keyword_list = _extract_search_keywords(title)
    if not keyword_list:
        return []
    seen_keys: set[tuple[str, str]] = set()
    all_cands: list[Tuple[models.ItemSummary, str]] = []
    per_query = max(limit // len(keyword_list), 50)
    for keywords in keyword_list[:3]:
        try:
            resp = browse.search_by_keywords(query=keywords, limit=per_query, offset=0)
        except Exception as e:
            logger.warning("キーワード検索失敗: q=%s, err=%s", keywords[:30], e)
            continue
        cands = _collect_candidates_to_check(
            resp, listing_item_id, seller_names, include_additional_images=True
        )
        for c, u in cands:
            k = (c.item_id, u)
            if k not in seen_keys:
                seen_keys.add(k)
                all_cands.append((c, u))
    return all_cands


def _collect_suspect_candidates(
    suspect_item_ids: list[str],
    token: str,
    listing_item_id: str,
    seller_names: list[str],
    max_images: int,
) -> list[Tuple[models.ItemSummary, str]]:
    """
    疑わしいアイテムを直接取得し、その全画像を候補として返す。
    eBay画像検索に引っかからないリサイズ流用も検知するため。
    """
    result: list[Tuple[models.ItemSummary, str]] = []
    for sid in suspect_item_ids:
        sid_clean = (sid or "").strip()
        if not sid_clean:
            continue
        try:
            suspect = item_fetcher.fetch_any_item_by_id(sid_clean, token)
        except Exception as e:
            logger.warning("疑わしいアイテム取得失敗: item_id=%s, err=%s", sid_clean, e)
            continue
        if not suspect:
            logger.warning("疑わしいアイテムが見つかりません: item_id=%s", sid_clean)
            continue
        if suspect.item_id == listing_item_id:
            continue
        if suspect.is_from_any_seller(seller_names):
            continue
        urls = suspect.image_urls(max_images)
        for url in urls:
            if url:
                result.append((suspect, url))
    return result


def _download_candidates_parallel(
    candidates: list[Tuple[models.ItemSummary, str]],
    max_workers: int,
) -> dict[str, bytes]:
    """候補画像を並列ダウンロード。"""
    if not candidates:
        return {}
    workers = max(1, min(max_workers, len(candidates)))
    cand_raw_map: dict[str, bytes] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_url = {
            executor.submit(_download_candidate_image, url): url
            for _, url in candidates
        }
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                raw = future.result()
                if raw is not None:
                    cand_raw_map[url] = raw
            except Exception:
                pass
    return cand_raw_map


def process_one_listing(
    conn: sqlite3.Connection,
    run_id: str,
    listing_item_id: str,
    item_summary: models.ItemSummary,
    params: RunParams,
    seller_names: list[str],
    token: str,
    skip_seller_check: bool = False,
    suspect_item_ids: Optional[list[str]] = None,
) -> Tuple[int, int, int, int]:
    """
    1出品を処理し、画像スキャン・候補チェック・検知を実行する。

    Returns:
        (scanned_images, candidates_checked, detections_new, listing_errors)
    """
    # 設定したセラー（EBAY_SELLER_USERNAME）の出品か検証。不一致なら処理しない（誤検知防止）
    # skip_seller_check: only_item で明示指定時はセラーチェックをスキップ
    if not skip_seller_check and not item_summary.is_from_any_seller(seller_names):
        return 0, 0, 0, 1

    scanned_images = 0
    candidates_checked = 0
    detections_new = 0
    listing_errors = 0

    # 疑わしいアイテム指定時は画像枚数を多めに（リサイズ流用は枚数が違う場合がある）
    max_imgs = max(params.max_images_per_listing, 12) if suspect_item_ids else params.max_images_per_listing
    image_urls = item_summary.image_urls(max_imgs)
    
    # 画像URLが空の場合のログ
    if not image_urls:
        logger.warning("画像URLが空: item_id=%s, title=%s, image=%s, additional_images=%d", 
                      listing_item_id, 
                      item_summary.title[:50] if item_summary.title else "None",
                      "有" if item_summary.image else "無",
                      len(item_summary.additional_images))
        return 0, 0, 0, 1  # 画像がない場合はエラーとしてカウント
    
    matched_this_image = False

    for img_index, img_url in enumerate(image_urls):
        # 画像ダウンロード
        try:
            raw = http.download_bytes(img_url)
        except Exception as e:
            logger.warning("画像ダウンロード失敗: item_id=%s, image_index=%d, url=%s, error=%s", 
                          listing_item_id, img_index, img_url[:100] if img_url else "None", str(e))
            listing_errors += 1
            continue

        if not raw or len(raw) == 0:
            logger.warning("画像データが空: item_id=%s, image_index=%d, url=%s", 
                          listing_item_id, img_index, img_url[:100] if img_url else "None")
            listing_errors += 1
            continue

        try:
            our_sha = hashing.sha256_hex(raw)
            our_phash = hashing.phash_image(raw)
            our_ahash = hashing.ahash_image(raw)
            our_dhash = hashing.dhash_image(raw)
        except Exception as e:
            logger.warning("画像ハッシュ計算失敗: item_id=%s, image_index=%d, error=%s", 
                          listing_item_id, img_index, str(e))
            listing_errors += 1
            continue

        image_b64 = to_base64_for_search(raw)
        if not image_b64:
            logger.warning("画像Base64変換失敗: item_id=%s, image_index=%d, url=%s", 
                          listing_item_id, img_index, img_url[:100] if img_url else "None")
            listing_errors += 1
            continue

        # 画像検索
        try:
            # marketplace_idを指定して検索（デフォルトはEBAY_US）
            search_resp = browse.search_by_image(
                image_b64,
                limit=params.candidates_per_image,
                offset=0,
                marketplace_id="EBAY_US",  # 画像検索はUSマーケットプレイスで実行
            )
        except Exception as e:
            error_detail = str(e)
            # HTTPエラーの場合は詳細を取得
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = f"{e.response.status_code}: {e.response.text[:200]}"
                except:
                    pass
            logger.warning("画像検索失敗: item_id=%s, image_index=%d, error=%s", 
                          listing_item_id, img_index, error_detail)
            listing_errors += 1
            continue

        scanned_images += 1
        matched_this_image = False

        candidates_to_check = _collect_candidates_to_check(
            search_resp, listing_item_id, seller_names
        )
        # キーワード検索で追加候補（画像検索に出ないリサイズ流用を一括で検知）
        if item_summary.title:
            kw_cands = _collect_keyword_candidates(
                item_summary.title,
                listing_item_id,
                seller_names,
                params.keyword_search_candidates,
            )
            seen_keys = {(c.item_id, u) for c, u in candidates_to_check}
            for kc, kurl in kw_cands:
                if (kc.item_id, kurl) not in seen_keys:
                    candidates_to_check.append((kc, kurl))
                    seen_keys.add((kc.item_id, kurl))
        # 疑わしいアイテムを直接追加（特定アイテムモード時のみ）
        if suspect_item_ids:
            # 疑わしいアイテムは画像枚数を多めに（12枚）取得して比較
            suspect_max_images = max(params.max_images_per_listing, 12)
            suspect_cands = _collect_suspect_candidates(
                suspect_item_ids,
                token,
                listing_item_id,
                seller_names,
                suspect_max_images,
            )
            # 重複を避ける（item_id + url が既にあればスキップ）
            seen_keys = {(c.item_id, u) for c, u in candidates_to_check}
            for sc, surl in suspect_cands:
                if (sc.item_id, surl) not in seen_keys:
                    candidates_to_check.append((sc, surl))
                    seen_keys.add((sc.item_id, surl))
        cand_raw_map = _download_candidates_parallel(
            candidates_to_check, params.max_concurrent_downloads
        )

        for candidate, cand_image_url in candidates_to_check:
            cand_raw = cand_raw_map.get(cand_image_url)
            if cand_raw is None:
                continue

            candidates_checked += 1
            their_sha = hashing.sha256_hex(cand_raw)
            their_phash = hashing.phash_image(cand_raw)
            their_ahash = hashing.ahash_image(cand_raw)
            their_dhash = hashing.dhash_image(cand_raw)
            result = matcher.check_match(
                our_sha,
                their_sha,
                our_image_url=img_url,
                their_image_url=cand_image_url,
                also_accept_same_image_url=params.also_accept_same_image_url,
                our_phash=our_phash,
                their_phash=their_phash,
                our_ahash=our_ahash,
                their_ahash=their_ahash,
                our_dhash=our_dhash,
                their_dhash=their_dhash,
            )
            if not result.match:
                continue
            if repo.detection_exists(conn, listing_item_id, candidate.item_id):
                continue

            subj, body = generator.generate_message(
                candidate.item_id,
                deadline_hours=params.deadline_hours,
                include_your_item_url=params.mention_next_steps,
                your_item_url=item_summary.item_web_url,
            )
            seller_display = (
                candidate.seller.display_name() if candidate.seller else ""
            )
            inserted = repo.insert_detection(
                conn,
                run_id,
                your_item_id=listing_item_id,
                your_item_url=item_summary.item_web_url,
                your_image_index=img_index,
                your_image_url=img_url,
                your_image_sha256=our_sha,
                infringing_item_id=candidate.item_id,
                infringing_item_url=candidate.item_web_url,
                infringing_seller_display=seller_display,
                infringing_image_url=cand_image_url,
                infringing_image_sha256=their_sha,
                match_evidence=result.evidence,
                message_subject=subj,
                message_body=body,
            )
            if inserted:
                detections_new += 1
                matched_this_image = True

            if params.stop_on_first_match_per_image and matched_this_image:
                break

        if params.stop_on_first_match_per_image and matched_this_image:
            break

    return scanned_images, candidates_checked, detections_new, listing_errors
