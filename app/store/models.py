"""ストア用データモデル。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class RunRow:
    run_id: str
    started_at: str
    finished_at: Optional[str]
    scanned_listings_count: int
    scanned_images_count: int
    candidates_checked_count: int
    detections_new_count: int
    errors_count: int
    notes: Optional[str]


@dataclass
class ListingScanStateRow:
    listing_item_id: str
    last_scanned_at: Optional[str]
    last_scanned_run_id: Optional[str]
    last_scan_status: Optional[str]  # success / partial / fail


@dataclass
class DetectionRow:
    detection_id: int
    run_id: str
    detected_at: str
    your_item_id: str
    your_item_url: str
    your_image_index: int
    your_image_url: str
    your_image_sha256: str
    infringing_item_id: str
    infringing_item_url: str
    infringing_seller_display: str
    infringing_image_url: str
    infringing_image_sha256: str
    match_evidence: str  # sha256 / url / both / phash / ahash / dhash
    status: str
    message_subject: Optional[str]
    message_body: Optional[str]
