"""検知結果の出力（CSV / Google Sheets）。"""
from __future__ import annotations

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from app.store.models import DetectionRow


def write_detections(
    detections: List["DetectionRow"],
    output_type: str,
    worksheet_name: str = "detections",
    image_preview_formula: bool = True,
) -> str:
    """
    検知結果を出力先に書き込む。
    Returns: 出力先パスまたは説明文字列（ログ用）。
    """
    if not detections:
        return ""

    if output_type == "csv":
        from app.output import csv_client

        csv_client.append_detections(detections)
        return str(csv_client.get_output_path())
    else:
        from app.sheets import client as sheets_client, schema as sheets_schema

        sheets_client.ensure_header_row(worksheet_name=worksheet_name)
        rows = [
            sheets_schema.detection_to_row(d, image_preview_formula)
            for d in detections
        ]
        sheets_client.append_detections(rows, worksheet_name=worksheet_name)
        return f"Google Sheets ({worksheet_name})"
