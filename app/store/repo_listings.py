"""listings_scan_state テーブルの CRUD。"""
from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Optional



def get_listings_scan_state_for_selection(
    conn: sqlite3.Connection, limit: int, known_listing_ids: list[str]
) -> list[tuple[str, Optional[str]]]:
    """
    対象出品を選ぶ: 最も古くスキャンされたものから limit 件。
    未登録（DB にないもの）を優先し、その後 last_scanned_at が古い順。
    """
    if not known_listing_ids:
        return []
    placeholders = ",".join("?" * len(known_listing_ids))
    existing = set(
        row[0]
        for row in conn.execute(
            f"SELECT listing_item_id FROM listings_scan_state "
            f"WHERE listing_item_id IN ({placeholders})",
            known_listing_ids,
        ).fetchall()
    )
    never_scanned = [lid for lid in known_listing_ids if lid not in existing]
    cursor = conn.execute(
        f"""
        SELECT listing_item_id, last_scanned_at
        FROM listings_scan_state
        WHERE listing_item_id IN ({placeholders})
        ORDER BY last_scanned_at IS NULL DESC, last_scanned_at ASC
        LIMIT ?
        """,
        known_listing_ids + [limit],
    )
    ordered_existing = [(row[0], row[1]) for row in cursor.fetchall()]
    result: list[tuple[str, Optional[str]]] = []
    for lid in never_scanned:
        if len(result) >= limit:
            break
        result.append((lid, None))
    for lid, last_at in ordered_existing:
        if len(result) >= limit:
            break
        result.append((lid, last_at))
    return result


def upsert_listing_scan_state(
    conn: sqlite3.Connection,
    listing_item_id: str,
    last_scanned_run_id: str,
    last_scan_status: str,
) -> None:
    """出品のスキャン状態を登録または更新。"""
    now = datetime.utcnow().isoformat() + "Z"
    conn.execute(
        """
        INSERT INTO listings_scan_state (
            listing_item_id, last_scanned_at, last_scanned_run_id, last_scan_status
        ) VALUES (?, ?, ?, ?)
        ON CONFLICT(listing_item_id) DO UPDATE SET
            last_scanned_at = excluded.last_scanned_at,
            last_scanned_run_id = excluded.last_scanned_run_id,
            last_scan_status = excluded.last_scan_status
        """,
        (listing_item_id, now, last_scanned_run_id, last_scan_status),
    )
    conn.commit()
