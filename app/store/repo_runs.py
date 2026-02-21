"""runs テーブルの CRUD。"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any, Optional

from app.store.models import RunRow


def _row_to_run(row: sqlite3.Row) -> RunRow:
    return RunRow(
        run_id=row["run_id"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        scanned_listings_count=row["scanned_listings_count"] or 0,
        scanned_images_count=row["scanned_images_count"] or 0,
        candidates_checked_count=row["candidates_checked_count"] or 0,
        detections_new_count=row["detections_new_count"] or 0,
        errors_count=row["errors_count"] or 0,
        notes=row["notes"],
    )


def create_run(conn: sqlite3.Connection, run_id: str) -> None:
    """新規 run を登録。"""
    now = datetime.utcnow().isoformat() + "Z"
    conn.execute(
        "INSERT INTO runs (run_id, started_at, scanned_listings_count, scanned_images_count, "
        "candidates_checked_count, detections_new_count, errors_count) "
        "VALUES (?, ?, 0, 0, 0, 0, 0)",
        (run_id, now),
    )
    conn.commit()


def update_run(
    conn: sqlite3.Connection,
    run_id: str,
    *,
    finished_at: Optional[str] = None,
    scanned_listings_count: Optional[int] = None,
    scanned_images_count: Optional[int] = None,
    candidates_checked_count: Optional[int] = None,
    detections_new_count: Optional[int] = None,
    errors_count: Optional[int] = None,
    notes: Optional[str] = None,
) -> None:
    """run を更新。"""
    updates: list[str] = []
    args: list[Any] = []
    if finished_at is not None:
        updates.append("finished_at = ?")
        args.append(finished_at)
    if scanned_listings_count is not None:
        updates.append("scanned_listings_count = ?")
        args.append(scanned_listings_count)
    if scanned_images_count is not None:
        updates.append("scanned_images_count = ?")
        args.append(scanned_images_count)
    if candidates_checked_count is not None:
        updates.append("candidates_checked_count = ?")
        args.append(candidates_checked_count)
    if detections_new_count is not None:
        updates.append("detections_new_count = ?")
        args.append(detections_new_count)
    if errors_count is not None:
        updates.append("errors_count = ?")
        args.append(errors_count)
    if notes is not None:
        updates.append("notes = ?")
        args.append(notes)
    if not updates:
        return
    args.append(run_id)
    conn.execute(f"UPDATE runs SET {', '.join(updates)} WHERE run_id = ?", args)
    conn.commit()


def get_run(conn: sqlite3.Connection, run_id: str) -> Optional[RunRow]:
    """run_id で run を取得。"""
    row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    return _row_to_run(row) if row else None


def get_last_run_finished_at(conn: sqlite3.Connection) -> Optional[str]:
    """直近の実行の finished_at を取得。未完了（NULL）は除外。"""
    row = conn.execute(
        "SELECT finished_at FROM runs WHERE finished_at IS NOT NULL "
        "ORDER BY finished_at DESC LIMIT 1"
    ).fetchone()
    return str(row[0]) if row and row[0] else None


def delete_run(conn: sqlite3.Connection, run_id: str) -> bool:
    """実行履歴を削除。紐づく検知・リストング状態も整理する。"""
    conn.execute("DELETE FROM detections WHERE run_id = ?", (run_id,))
    conn.execute(
        "UPDATE listings_scan_state SET last_scanned_run_id = NULL WHERE last_scanned_run_id = ?",
        (run_id,),
    )
    cursor = conn.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
    conn.commit()
    return cursor.rowcount > 0
