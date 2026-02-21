"""CSV ファイルに検知結果を出力。Google Cloud 不要。"""
from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from app.store.models import DetectionRow

from app.sheets import schema

# デフォルト出力先
DEFAULT_CSV_PATH = "data/detections.csv"


def get_output_path() -> Path:
    path = os.getenv("DETECTIONS_CSV_PATH", DEFAULT_CSV_PATH)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def append_detections(
    detections: List["DetectionRow"],
    csv_path: str | Path | None = None,
) -> None:
    """検知結果を CSV に追記。ヘッダーがなければ先頭行に書き込む。"""
    path = Path(csv_path) if csv_path else get_output_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    file_exists = path.exists()
    with open(path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(schema.COLUMNS)
        for d in detections:
            row = schema.detection_to_row(d, image_preview_formula=False)
            writer.writerow(row)
