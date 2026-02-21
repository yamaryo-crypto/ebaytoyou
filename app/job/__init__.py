"""ジョブ実行パッケージ。CLI / Web から run_once を呼び出す。"""
from app.job.runner import run_once

__all__ = ["run_once"]
