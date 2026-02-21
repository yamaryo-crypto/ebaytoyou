"""ジョブ実行パラメータ。"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# 40品以下だと全件取得できない不具合があったため、40以下は200に補正
MIN_LISTINGS_FOR_FULL_SCAN = 41


@dataclass(frozen=True)
class RunParams:
    """1回のジョブ実行のパラメータ。"""

    max_listings: int
    max_images_per_listing: int
    candidates_per_image: int
    keyword_search_candidates: int
    stop_on_first_match_per_image: bool
    max_concurrent_downloads: int
    search_limit: int
    search_sort: str
    also_accept_same_image_url: bool
    output_type: str  # "csv" | "sheets"
    worksheet_name: str
    image_preview_formula: bool
    deadline_hours: int
    mention_next_steps: bool

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> RunParams:
        run_cfg = config.get("run", {})
        ebay_cfg = config.get("ebay", {})
        match_cfg = config.get("match", {})
        sheet_cfg = config.get("sheet", {})
        msg_cfg = config.get("message", {})

        max_listings = int(run_cfg.get("max_listings_per_run", 1000))
        search_limit = int(ebay_cfg.get("search_limit", 1000))
        if max_listings < MIN_LISTINGS_FOR_FULL_SCAN:
            logger.warning(
                "max_listings_per_run=%d は40以下です。40品以上スキャンするため200に補正しました。",
                max_listings,
            )
            max_listings = 200
        if search_limit < MIN_LISTINGS_FOR_FULL_SCAN:
            logger.warning(
                "search_limit=%d は40以下です。40品以上取得するため200に補正しました。",
                search_limit,
            )
            search_limit = 200

        return cls(
            max_listings=max_listings,
            max_images_per_listing=int(run_cfg.get("max_images_per_listing", 3)),
            candidates_per_image=int(run_cfg.get("candidates_per_image", 50)),
            keyword_search_candidates=int(run_cfg.get("keyword_search_candidates", 100)),
            stop_on_first_match_per_image=bool(
                run_cfg.get("stop_on_first_match_per_image", True)
            ),
            max_concurrent_downloads=int(run_cfg.get("max_concurrent_downloads", 10)),
            search_limit=search_limit,
            search_sort=ebay_cfg.get("search_sort") or "newlyListed",
            also_accept_same_image_url=bool(
                match_cfg.get("also_accept_same_image_url", True)
            ),
            output_type=sheet_cfg.get("output_type", "csv"),
            worksheet_name=sheet_cfg.get("worksheet_name", "detections"),
            image_preview_formula=bool(sheet_cfg.get("image_preview_formula", True)),
            deadline_hours=int(msg_cfg.get("deadline_hours", 24)),
            mention_next_steps=bool(msg_cfg.get("mention_next_steps", True)),
        )
