"""テンプレのプレースホルダを埋めて件名・本文を生成。"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from app.msg import templates


def deadline_jst(hours: int = 24, from_now: Optional[datetime] = None) -> str:
    """from_now から hours 後を JST でフォーマット。例: 2026-02-05 15:00 JST"""
    base = from_now or datetime.now(timezone.utc)
    jst = ZoneInfo("Asia/Tokyo")
    deadline = base + timedelta(hours=hours)
    return deadline.astimezone(jst).strftime("%Y-%m-%d %H:%M JST")


def generate_message(
    infringing_item_id: str,
    deadline_hours: int = 24,
    include_your_item_url: bool = False,
    your_item_url: str = "",
) -> tuple[str, str]:
    """(subject, body) を返す。"""
    subject = templates.SUBJECT
    deadline_str = deadline_jst(hours=deadline_hours)
    body = templates.BODY_JA.format(
        infringing_item_id=infringing_item_id,
        deadline_jst=deadline_str,
    )
    if include_your_item_url and your_item_url:
        body = body + "\n\n（参考）当方の出品: " + your_item_url
    return subject, body
