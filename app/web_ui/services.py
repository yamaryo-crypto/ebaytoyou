"""
Web UI 用サービス集約エントリポイント。
ジョブ実行・データ取得の API を提供。
"""
from __future__ import annotations

from app.web_ui.data_queries import get_detections_dataframe, get_runs_dataframe
from app.web_ui.job_runner import run_job_in_thread, sync_job_state_to_session, cancel_job

__all__ = [
    "run_job_in_thread",
    "sync_job_state_to_session",
    "get_runs_dataframe",
    "get_detections_dataframe",
    "cancel_job",
]
