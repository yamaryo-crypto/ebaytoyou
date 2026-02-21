"""ジョブ実行のオーケストレーション。"""
from __future__ import annotations

import logging
import os
import sys
from typing import Callable, Optional

from app.config import load_config
from app.constants import DEFAULT_SELLER_USERNAME
from app.ebay import auth
from app.ebay.models import ItemSummary
from app.ebay.item_fetcher import fetch_item_by_id
from app.job.listing_selector import select_listings, compute_listing_status
from app.job.output_writer import write_detections
from app.job.params import RunParams
from app.job.processor import process_one_listing
from app.store import db, repo
from app.util.datetime_utils import run_id as make_run_id, utc_now_iso
from app.util.log import get_logger, log_run_summary, setup_logging


def run_once(
    dry_run: bool = False,
    only_item: Optional[str] = None,
    suspect_item_ids: Optional[list[str]] = None,
    run_overrides: Optional[dict] = None,
    progress_callback: Optional[
        Callable[[int, int, int, int], None]
    ] = None,
    cancellation_check: Optional[Callable[[], bool]] = None,
) -> None:
    """
    1回のジョブ実行。出品検索 → 画像スキャン → 侵害検知 → 出力。
    run_overrides: 実行時オーバーライド（max_listings_per_run, candidates_per_image など）
    """
    setup_logging()
    logger = get_logger("main")
    config = load_config()
    if run_overrides:
        run_cfg = config.setdefault("run", {})
        ebay_cfg = config.setdefault("ebay", {})
        for k, v in run_overrides.items():
            if k in ("max_listings_per_run", "max_images_per_listing", "candidates_per_image",
                     "stop_on_first_match_per_image", "max_concurrent_downloads"):
                run_cfg[k] = v
            elif k == "search_limit":
                ebay_cfg[k] = v
    params = RunParams.from_config(config)
    seller_username = os.getenv("EBAY_SELLER_USERNAME", DEFAULT_SELLER_USERNAME)

    run_id = make_run_id()
    if dry_run:
        _handle_dry_run(logger, run_id, params, only_item)
        return

    conn = db.get_connection()
    db.init_schema(conn)
    repo.create_run(conn, run_id)

    try:
        token = auth.get_access_token()
    except Exception as e:
        logger.exception("OAuth failed: %s", e)
        repo.update_run(conn, run_id, finished_at=utc_now_iso(), errors_count=1, notes="OAuth failed")
        log_run_summary(logger, run_id, 0, 0, 0, 0, 1, notes="OAuth failed")
        sys.exit(1)

    scanned = 0
    images_scanned = 0
    candidates_checked = 0
    detections_new = 0
    errors_count = 0

    from_beginning = bool((run_overrides or {}).get("from_beginning", True))
    try:
        selected, summary_map, seller_names = select_listings(
            conn,
            params,
            seller_username,
            only_item,
            from_beginning=from_beginning,
        )

        total = len(selected)
        logger.info("処理開始: 対象=%d件", total)
        if progress_callback:
            progress_callback(0, total, 0, 0)
        for idx, (listing_item_id, _last_scanned) in enumerate(selected):
            # キャンセルチェック
            if cancellation_check and cancellation_check():
                logger.info("実行が中止されました。処理済み: %d / %d 件", scanned, total)
                repo.update_run(
                    conn, run_id,
                    scanned_listings_count=scanned,
                    scanned_images_count=images_scanned,
                    candidates_checked_count=candidates_checked,
                    detections_new_count=detections_new,
                    errors_count=errors_count,
                    notes=f"User cancelled. Processed {scanned}/{total} items",
                )
                return
            
            if progress_callback:
                progress_callback(scanned, total, images_scanned, candidates_checked)

            item_summary = _resolve_item_summary(
                listing_item_id,
                summary_map,
                only_item,
                token,
                params,
                seller_names,
                logger,
            )
            if item_summary is None:
                if only_item:
                    repo.upsert_listing_scan_state(conn, listing_item_id, run_id, "fail")
                    errors_count += 1
                    repo.update_run(
                        conn, run_id,
                        notes=f"Item {listing_item_id} not found (API fetch failed or invalid ID)",
                    )
                continue

            suspect_ids = suspect_item_ids or (run_overrides or {}).get("suspect_item_ids")
            img_count, cand_count, det_count, listing_errors = process_one_listing(
                conn,
                run_id,
                listing_item_id,
                item_summary,
                params,
                seller_names,
                token,
                skip_seller_check=bool(only_item),
                suspect_item_ids=suspect_ids,
            )
            scanned += 1
            images_scanned += img_count
            candidates_checked += cand_count
            detections_new += det_count
            errors_count += listing_errors

            status = compute_listing_status(
                listing_errors, item_summary.image_urls(params.max_images_per_listing)
            )
            repo.upsert_listing_scan_state(conn, listing_item_id, run_id, status)
            if scanned % 50 == 0 or scanned == total:
                logger.info("処理中: %d / %d 件目 (スキャン済=%d, 画像=%d)", scanned, total, scanned, images_scanned)
            if progress_callback:
                progress_callback(scanned, total, images_scanned, candidates_checked)

        repo.update_run(
            conn,
            run_id,
            scanned_listings_count=scanned,
            scanned_images_count=images_scanned,
            candidates_checked_count=candidates_checked,
            detections_new_count=detections_new,
            errors_count=errors_count,
        )

        new_detections = repo.get_detections_by_run(conn, run_id)
        if new_detections:
            try:
                dest = write_detections(
                    new_detections,
                    output_type=params.output_type,
                    worksheet_name=params.worksheet_name,
                    image_preview_formula=params.image_preview_formula,
                )
                logger.info("Detections appended to %s", dest)
            except Exception as e:
                logger.exception("Output failed: %s", e)
                repo.update_run(conn, run_id, notes=f"Output failed: {e}")
                errors_count += 1
    except Exception as e:
        logger.exception("Run error: %s", e)
        errors_count += 1
        repo.update_run(
            conn, run_id,
            scanned_listings_count=scanned,
            scanned_images_count=images_scanned,
            candidates_checked_count=candidates_checked,
            detections_new_count=detections_new,
            errors_count=errors_count,
            notes=str(e),
        )
    finally:
        # finished_at を更新（カウントは既に更新済み）
        repo.update_run(conn, run_id, finished_at=utc_now_iso())
        run = repo.get_run(conn, run_id)
        if run:
            log_run_summary(
                logger,
                run_id,
                run.scanned_listings_count,
                run.scanned_images_count,
                run.candidates_checked_count,
                run.detections_new_count,
                run.errors_count,
                run.notes or "",
            )


def _resolve_item_summary(
    listing_item_id: str,
    summary_map: dict[str, ItemSummary],
    only_item: Optional[str],
    token: str,
    params: RunParams,
    seller_names: list[str],
    logger: logging.Logger,
) -> Optional[ItemSummary]:
    """出品の ItemSummary を解決。only_item 時は fetch_item_by_id で取得。"""
    item_summary = summary_map.get(listing_item_id)
    first_seller = seller_names[0] if seller_names else ""
    fetched_via_only_item = False
    if only_item and not item_summary:
        item_summary = fetch_item_by_id(
            listing_item_id,
            token,
            params.search_limit,
            params.search_sort,
            first_seller,
        )
        if not item_summary:
            logger.warning("Item %s not found", listing_item_id)
            return None
        fetched_via_only_item = True

    if not item_summary:
        logger.warning("Listing %s not in search result, skip", listing_item_id)
        return None

    # only_item で明示指定された場合はセラーチェックをスキップ
    # （EBAY_SELLER_USERNAME がストア名と異なる場合や複数アカウント対応）
    if not fetched_via_only_item and not item_summary.is_from_any_seller(seller_names):
        logger.warning(
            "Listing %s is not from seller %s (seller=%s), skip",
            listing_item_id,
            seller_names,
            item_summary.seller.display_name() if item_summary.seller else "unknown",
        )
        return None

    return item_summary


def _handle_dry_run(
    logger: logging.Logger,
    run_id: str,
    params: RunParams,
    only_item: Optional[str],
) -> None:
    max_listings = 1 if only_item else params.max_listings
    logger.info("dry-run: run_id=%s, only_item=%s", run_id, only_item)
    logger.info(
        "dry-run: would get token, search my listings, select up to %s listings",
        max_listings,
    )
    log_run_summary(logger, run_id, 0, 0, 0, 0, 0, notes="dry-run")


