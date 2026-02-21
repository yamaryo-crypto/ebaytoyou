"""SQLite テーブル作成と接続。"""
import os
import sqlite3
from pathlib import Path
from typing import Optional

# デフォルトはプロジェクトルートの data/state.db
def _default_db_path() -> str:
    base = Path(__file__).resolve().parent.parent.parent
    data_dir = base / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir / "state.db")

def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or os.getenv("STATE_DB_PATH") or _default_db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            scanned_listings_count INTEGER DEFAULT 0,
            scanned_images_count INTEGER DEFAULT 0,
            candidates_checked_count INTEGER DEFAULT 0,
            detections_new_count INTEGER DEFAULT 0,
            errors_count INTEGER DEFAULT 0,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS listings_scan_state (
            listing_item_id TEXT PRIMARY KEY,
            last_scanned_at TEXT,
            last_scanned_run_id TEXT,
            last_scan_status TEXT,
            FOREIGN KEY (last_scanned_run_id) REFERENCES runs(run_id)
        );

        CREATE TABLE IF NOT EXISTS detections (
            detection_id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            detected_at TEXT NOT NULL,
            your_item_id TEXT NOT NULL,
            your_item_url TEXT NOT NULL,
            your_image_index INTEGER NOT NULL,
            your_image_url TEXT NOT NULL,
            your_image_sha256 TEXT NOT NULL,
            infringing_item_id TEXT NOT NULL,
            infringing_item_url TEXT NOT NULL,
            infringing_seller_display TEXT NOT NULL,
            infringing_image_url TEXT NOT NULL,
            infringing_image_sha256 TEXT NOT NULL,
            match_evidence TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'NEW',
            message_subject TEXT,
            message_body TEXT,
            UNIQUE(your_item_id, infringing_item_id),
            FOREIGN KEY (run_id) REFERENCES runs(run_id)
        );

        CREATE INDEX IF NOT EXISTS idx_detections_run_id ON detections(run_id);
        CREATE INDEX IF NOT EXISTS idx_detections_status ON detections(status);
        CREATE INDEX IF NOT EXISTS idx_listings_scan_state_last_scanned ON listings_scan_state(last_scanned_at);
    """)
    conn.commit()
