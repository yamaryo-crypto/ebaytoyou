"""Web UI 用ジョブ実行（スレッド内実行）。"""
from __future__ import annotations

import io
import logging
import sys
import threading
from typing import Any, Optional

# スレッドから session_state を更新すると ScriptRunContext エラーになるため、
# スレッドはこの共有 dict に書き込み、メインスクリプトが session_state に反映する。
_job_state: dict[str, Any] = {
    "status": None,
    "logs": [],
    "progress": None,  # {"scanned": int, "total": int, "images_scanned": int, "candidates_checked": int}
    "cancelled": False,  # 中止フラグ
}


class _LogCapture(io.StringIO):
    """ログをリストに蓄積する StringIO。"""

    def __init__(self, logs_ref: list[str]) -> None:
        super().__init__()
        self._logs_ref = logs_ref

    def write(self, s: str) -> int:
        if s.strip():
            self._logs_ref.append(s.strip())
        return len(s)


class _ListHandler(logging.Handler):
    """logging の出力をリストに追加するハンドラ。実行ログに logger.info 等を表示するため。"""

    def __init__(self, logs_ref: list[str]) -> None:
        super().__init__()
        self._logs_ref = logs_ref

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            if msg.strip():
                self._logs_ref.append(msg.strip())
        except Exception:
            self.handleError(record)


def _run_job_worker(
    dry_run: bool,
    only_item: Optional[str],
    run_overrides: Optional[dict],
) -> None:
    """スレッド内でジョブを実行。_job_state に結果を書き込む。"""
    from app.job import run_once

    _job_state["status"] = "running"
    _job_state["logs"] = []
    _job_state["progress"] = None
    _job_state["cancelled"] = False  # 中止フラグをリセット
    logs_ref: list[str] = []

    def _on_progress(scanned: int, total: int, images_scanned: int, candidates_checked: int) -> None:
        _job_state["progress"] = {
            "scanned": scanned,
            "total": total,
            "images_scanned": images_scanned,
            "candidates_checked": candidates_checked,
        }

    try:
        old_stdout = sys.stdout
        sys.stdout = _LogCapture(logs_ref)
        # logger.info 等も実行ログに表示するため、ルートロガーにハンドラを追加
        root = logging.getLogger()
        list_handler = _ListHandler(logs_ref)
        list_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S"))
        root.addHandler(list_handler)
        try:
            run_once(
                dry_run=dry_run,
                only_item=only_item,
                run_overrides=run_overrides,
                progress_callback=_on_progress,
                cancellation_check=lambda: _job_state.get("cancelled", False),
            )
            if _job_state.get("cancelled", False):
                _job_state["status"] = "cancelled"
                _job_state["logs"].append("ユーザーによって実行が中止されました。")
            else:
                _job_state["status"] = "completed"
        finally:
            root.removeHandler(list_handler)
            sys.stdout = old_stdout
            _job_state["logs"] = logs_ref[-100:]
    except Exception as e:
        _job_state["status"] = "error"
        _job_state["logs"] = logs_ref + [f"エラー: {str(e)}"]
        import traceback

        _job_state["logs"].append(traceback.format_exc())


def run_job_in_thread(
    dry_run: bool,
    only_item: Optional[str],
    run_overrides: Optional[dict] = None,
) -> None:
    """ジョブをスレッドで開始。完了後は sync_job_state_to_session で状態を取得。"""
    _job_state["status"] = "running"
    _job_state["logs"] = []
    _job_state["progress"] = None
    _job_state["cancelled"] = False  # 中止フラグをリセット
    thread = threading.Thread(
        target=_run_job_worker,
        args=(dry_run, only_item, run_overrides),
        daemon=True,
    )
    thread.start()


def cancel_job() -> None:
    """実行中のジョブを中止する。"""
    _job_state["cancelled"] = True


def sync_job_state_to_session() -> None:
    """スレッドの実行結果（_job_state）を st.session_state に反映。"""
    import streamlit as st

    if _job_state["status"] is not None:
        st.session_state.run_status = _job_state["status"]
        st.session_state.run_logs = _job_state["logs"]
        st.session_state.run_progress = _job_state.get("progress")
