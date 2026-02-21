"""Google スプレッドシートの列スキーマ（detections ワークシート）。"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.store.models import DetectionRow

# 列順（必須＋推奨）
COLUMNS = [
    "detected_at",
    "your_item_id",
    "your_item_url",
    "infringing_seller_display",
    "infringing_item_url",
    "infringing_item_id",
    "infringing_image_preview",  # =IMAGE(url) または URL
    "match_evidence",
    "message_subject",
    "message_body",
    "status",
]


def detection_to_row(detection: DetectionRow, image_preview_formula: bool = True) -> list:
    """DetectionRow をシート1行分のリストに変換。"""
    preview = f'=IMAGE("{detection.infringing_image_url}")' if image_preview_formula else detection.infringing_image_url
    return [
        detection.detected_at,
        detection.your_item_id,
        detection.your_item_url,
        detection.infringing_seller_display,
        detection.infringing_item_url,
        detection.infringing_item_id,
        preview,
        detection.match_evidence,
        detection.message_subject or "",
        detection.message_body or "",
        detection.status,
    ]
