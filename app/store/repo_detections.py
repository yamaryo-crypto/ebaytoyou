"""detections テーブルの CRUD。"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Optional

from app.store.models import DetectionRow


def _row_to_detection(row: sqlite3.Row) -> DetectionRow:
    return DetectionRow(
        detection_id=row["detection_id"],
        run_id=row["run_id"],
        detected_at=row["detected_at"],
        your_item_id=row["your_item_id"],
        your_item_url=row["your_item_url"],
        your_image_index=row["your_image_index"],
        your_image_url=row["your_image_url"],
        your_image_sha256=row["your_image_sha256"],
        infringing_item_id=row["infringing_item_id"],
        infringing_item_url=row["infringing_item_url"],
        infringing_seller_display=row["infringing_seller_display"],
        infringing_image_url=row["infringing_image_url"],
        infringing_image_sha256=row["infringing_image_sha256"],
        match_evidence=row["match_evidence"],
        status=row["status"],
        message_subject=row["message_subject"],
        message_body=row["message_body"],
    )


def detection_exists(
    conn: sqlite3.Connection, your_item_id: str, infringing_item_id: str
) -> bool:
    """検知が既に登録されているか。"""
    row = conn.execute(
        "SELECT 1 FROM detections WHERE your_item_id = ? AND infringing_item_id = ?",
        (your_item_id, infringing_item_id),
    ).fetchone()
    return row is not None


def insert_detection(
    conn: sqlite3.Connection,
    run_id: str,
    your_item_id: str,
    your_item_url: str,
    your_image_index: int,
    your_image_url: str,
    your_image_sha256: str,
    infringing_item_id: str,
    infringing_item_url: str,
    infringing_seller_display: str,
    infringing_image_url: str,
    infringing_image_sha256: str,
    match_evidence: str,
    message_subject: str,
    message_body: str,
) -> Optional[DetectionRow]:
    """検知を登録。重複時は None。"""
    now = datetime.utcnow().isoformat() + "Z"
    try:
        cursor = conn.execute(
            """
            INSERT INTO detections (
                run_id, detected_at, your_item_id, your_item_url, your_image_index,
                your_image_url, your_image_sha256, infringing_item_id, infringing_item_url,
                infringing_seller_display, infringing_image_url, infringing_image_sha256,
                match_evidence, status, message_subject, message_body
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'NEW', ?, ?)
            """,
            (
                run_id, now, your_item_id, your_item_url, your_image_index,
                your_image_url, your_image_sha256, infringing_item_id, infringing_item_url,
                infringing_seller_display, infringing_image_url, infringing_image_sha256,
                match_evidence, message_subject, message_body,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM detections WHERE detection_id = ?", (cursor.lastrowid,)
        ).fetchone()
        return _row_to_detection(row) if row else None
    except sqlite3.IntegrityError:
        conn.rollback()
        return None


def get_detections_by_run(conn: sqlite3.Connection, run_id: str) -> list[DetectionRow]:
    """run_id に紐づく検知一覧を取得。"""
    rows = conn.execute(
        "SELECT * FROM detections WHERE run_id = ? ORDER BY detection_id", (run_id,)
    ).fetchall()
    return [_row_to_detection(r) for r in rows]


def get_detections_not_synced_to_sheet(
    conn: sqlite3.Connection,
) -> list[DetectionRow]:
    """シート未出力の検知（status='NEW'）を取得。"""
    rows = conn.execute(
        "SELECT * FROM detections WHERE status = 'NEW' ORDER BY detection_id"
    ).fetchall()
    return [_row_to_detection(r) for r in rows]


def get_detection(conn: sqlite3.Connection, detection_id: int) -> Optional[DetectionRow]:
    """detection_id で検知を取得。"""
    row = conn.execute(
        "SELECT * FROM detections WHERE detection_id = ?", (detection_id,)
    ).fetchone()
    return _row_to_detection(row) if row else None


def delete_detection(conn: sqlite3.Connection, detection_id: int) -> bool:
    """検知を削除。存在すれば True、しなければ False。"""
    cursor = conn.execute("DELETE FROM detections WHERE detection_id = ?", (detection_id,))
    conn.commit()
    return cursor.rowcount > 0


def update_detection_status(
    conn: sqlite3.Connection, detection_id: int, status: str
) -> bool:
    """検知のステータスを更新。存在すれば True、しなければ False。"""
    cursor = conn.execute(
        "UPDATE detections SET status = ? WHERE detection_id = ?",
        (status, detection_id),
    )
    conn.commit()
    return cursor.rowcount > 0
