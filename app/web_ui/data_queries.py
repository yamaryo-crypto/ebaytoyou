"""Web UI 用データ取得（実行履歴・検知結果）。"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from app.store import db


def get_runs_dataframe() -> pd.DataFrame:
    """実行履歴を DataFrame で取得。常にDBから最新を読み込む。"""
    conn = db.get_connection()
    db.init_schema(conn)
    try:
        rows = conn.execute(
            "SELECT * FROM runs ORDER BY started_at DESC LIMIT 50"
        ).fetchall()
    finally:
        conn.close()
    if not rows:
        return pd.DataFrame()
    data = [
        {
            "実行ID": r["run_id"],
            "開始時刻": r["started_at"],
            "終了時刻": r["finished_at"] or "実行中",
            "処理出品数": r["scanned_listings_count"] or 0,
            "スキャン画像数": r["scanned_images_count"] or 0,
            "候補チェック数": r["candidates_checked_count"] or 0,
            "新規検知数": r["detections_new_count"] or 0,
            "エラー数": r["errors_count"] or 0,
            "備考": r["notes"] or "",
        }
        for r in rows
    ]
    return pd.DataFrame(data)


def get_detections_dataframe(limit: int = 100, include_messages: bool = False) -> pd.DataFrame:
    """
    検知結果を DataFrame で取得。常にDBから最新を読み込む。
    include_messages=True の場合、メッセージ文面（件名・本文）も含める（CSV出力用）。
    """
    conn = db.get_connection()
    db.init_schema(conn)
    try:
        rows = conn.execute(
            "SELECT * FROM detections ORDER BY detected_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    if not rows:
        return pd.DataFrame()
    data = [
        {
            "detection_id": d["detection_id"],
            "検知日時": d["detected_at"],
            "あなたの出品ID": d["your_item_id"],
            "あなたの出品URL": d["your_item_url"],
            "侵害セラー": d["infringing_seller_display"],
            "侵害出品ID": d["infringing_item_id"],
            "侵害出品URL": d["infringing_item_url"],
            "一致証拠": d["match_evidence"],
            "ステータス": d["status"],
        }
        for d in rows
    ]
    if include_messages:
        for i, d in enumerate(rows):
            data[i]["メッセージ件名"] = d["message_subject"] or ""
            data[i]["メッセージ本文"] = d["message_body"] or ""
    return pd.DataFrame(data)


def get_detection_by_id(detection_id: int) -> Optional[dict]:
    """検知IDで検知情報を取得。"""
    from app.store import repo
    
    conn = db.get_connection()
    db.init_schema(conn)
    try:
        detection = repo.get_detection(conn, detection_id)
        if not detection:
            return None
        return {
            "detection_id": detection.detection_id,
            "侵害セラー": detection.infringing_seller_display,
            "侵害出品ID": detection.infringing_item_id,
            "侵害出品URL": detection.infringing_item_url,
            "メッセージ件名": detection.message_subject or "",
            "メッセージ本文": detection.message_body or "",
            "ステータス": detection.status,
        }
    finally:
        conn.close()
