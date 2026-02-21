"""
ストアリポジトリの集約エントリポイント。
runs / listings_scan_state / detections の CRUD を一元提供。
"""
from __future__ import annotations

from app.store.repo_runs import create_run, delete_run, get_run, get_last_run_finished_at, update_run
from app.store.repo_listings import (
    get_listings_scan_state_for_selection,
    upsert_listing_scan_state,
)
from app.store.repo_detections import (
    delete_detection,
    detection_exists,
    get_detection,
    get_detections_by_run,
    get_detections_not_synced_to_sheet,
    insert_detection,
    update_detection_status,
)

__all__ = [
    "create_run",
    "delete_detection",
    "delete_run",
    "update_run",
    "get_run",
    "get_last_run_finished_at",
    "get_listings_scan_state_for_selection",
    "upsert_listing_scan_state",
    "detection_exists",
    "get_detection",
    "insert_detection",
    "get_detections_by_run",
    "get_detections_not_synced_to_sheet",
    "update_detection_status",
]
