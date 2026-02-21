"""簡易ロギング。runサマリを必ず出せるようにする。"""
import logging
import sys
from typing import Any

def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

def log_run_summary(
    logger: logging.Logger,
    run_id: str,
    scanned_listings_count: int,
    scanned_images_count: int,
    candidates_checked_count: int,
    detections_new_count: int,
    errors_count: int,
    notes: str = "",
    **extra: Any,
) -> None:
    logger.info(
        "run_summary run_id=%s scanned_listings=%s scanned_images=%s candidates_checked=%s detections_new=%s errors=%s notes=%s",
        run_id,
        scanned_listings_count,
        scanned_images_count,
        candidates_checked_count,
        detections_new_count,
        errors_count,
        notes or "(none)",
        extra=extra,
    )
