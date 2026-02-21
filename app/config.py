"""設定の読み込み・保存。main / web で共有。"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent


def default_config() -> dict[str, Any]:
    """デフォルト設定を返す。"""
    return {
        "run": {
            "timezone": "Asia/Tokyo",
            "max_listings_per_run": 1000,  # 初期値1000（全件スキャン向け）
            "max_images_per_listing": 3,
            "candidates_per_image": 100,  # 侵害検知向上のため100（50だと候補外になる場合あり）
            "stop_on_first_match_per_image": True,
            "max_concurrent_downloads": 10,
        },
        "ebay": {"search_limit": 1000, "search_sort": "newlyListed"},
        "match": {"mode": "sha256_exact", "also_accept_same_image_url": True},
        "sheet": {
            "output_type": "csv",
            "worksheet_name": "detections",
            "append_only": False,
            "image_preview_formula": True,
        },
        "message": {
            "language": "ja",
            "tone": "strong",
            "deadline_hours": 24,
            "mention_next_steps": True,
        },
    }


def load_config(config_path: Optional[str] = None) -> dict[str, Any]:
    """config.yaml を読み込む。存在しなければデフォルトを返す。読み込みエラー時もデフォルトを返す。"""
    path = config_path or os.getenv("CONFIG_PATH") or str(ROOT / "config.yaml")
    if not os.path.isfile(path):
        return default_config()
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or default_config()
    except Exception:
        return default_config()


def save_config(config: dict[str, Any], config_path: Optional[str] = None) -> None:
    """config.yaml に保存する。"""
    path = config_path or str(ROOT / "config.yaml")
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)


def load_env(env_path: Optional[str] = None) -> dict[str, str]:
    """.env ファイルを読み込む。"""
    path = env_path or str(ROOT / ".env")
    env: dict[str, str] = {}
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env[key.strip()] = value.strip()
    return env


def save_env(env: dict[str, str], env_path: Optional[str] = None) -> None:
    """.env ファイルに保存する。"""
    path = env_path or str(ROOT / ".env")
    with open(path, "w", encoding="utf-8") as f:
        for key, value in env.items():
            f.write(f"{key}={value}\n")
