"""日時ユーティリティ。"""
from __future__ import annotations

from datetime import datetime, timezone


def run_id() -> str:
    """ジョブ実行ID（UTC タイムスタンプ）。"""
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def utc_now_iso() -> str:
    """UTC 現在時刻の ISO 形式文字列。"""
    return datetime.now(timezone.utc).isoformat() + "Z"
