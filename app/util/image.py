"""画像処理ユーティリティ。"""
from __future__ import annotations

import base64
import io
from typing import Optional


def to_base64_for_search(raw: bytes) -> Optional[str]:
    """
    画像を JPEG に変換して Base64 化。search_by_image 用。
    RGBA/PNG などは JPEG に変換し、変換失敗時はそのまま Base64 を試行する。
    """
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(raw))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception:
        try:
            return base64.b64encode(raw).decode("ascii")
        except Exception:
            return None
