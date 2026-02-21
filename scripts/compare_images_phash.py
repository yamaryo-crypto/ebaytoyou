#!/usr/bin/env python3
"""
eBay 画像盗用検知用: Perceptual Hash による類似度判定スクリプト。

2つの画像URLを入力とし、imagehash.phash() でハミング距離を計算。
リサイズ・再圧縮されていても見た目が同じ画像を検知する。

使用例:
    python scripts/compare_images_phash.py "https://example.com/img1.jpg" "https://example.com/img2.jpg"
"""
from __future__ import annotations

import io
import sys
from typing import Optional, Tuple

import requests
from PIL import Image

try:
    import imagehash
except ImportError:
    print("imagehash をインストールしてください: pip install imagehash")
    sys.exit(1)


def download_image(url: str, timeout: int = 30) -> Optional[bytes]:
    """画像URLをダウンロードしてバイト列を返す。失敗時は None。"""
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.content
    except requests.RequestException as e:
        print(f"ダウンロード失敗: {url} - {e}")
        return None


def load_and_phash(image_data: bytes) -> Optional[imagehash.ImageHash]:
    """画像バイト列から phash を計算。"""
    try:
        img = Image.open(io.BytesIO(image_data))
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        return imagehash.phash(img)
    except Exception as e:
        print(f"画像読み込み/ハッシュ計算失敗: {e}")
        return None


def compare_images(url1: str, url2: str) -> Tuple[int, str]:
    """
    2つの画像URLを比較し、Perceptual Hash のハミング距離と判定コメントを返す。

    Returns:
        (distance: int, comment: str)
        - distance: ハミング距離（0 = 完全一致）
        - comment: 判定コメント

    判定基準:
        - 距離 0〜5: 同一画像の可能性が極めて高い（盗用）
        - 距離 6〜10: 似ているが加工されている可能性あり
        - 距離 11以上: 異なる画像
    """
    data1 = download_image(url1)
    data2 = download_image(url2)
    if data1 is None or data2 is None:
        return -1, "画像の取得に失敗しました"

    hash1 = load_and_phash(data1)
    hash2 = load_and_phash(data2)
    if hash1 is None or hash2 is None:
        return -1, "ハッシュの計算に失敗しました"

    distance = hash1 - hash2
    distance_int = int(distance)

    if distance_int <= 5:
        comment = "同一画像の可能性が極めて高い（盗用）"
    elif distance_int <= 10:
        comment = "似ているが加工されている可能性あり"
    else:
        comment = "異なる画像"

    return distance_int, comment


def main() -> None:
    if len(sys.argv) != 3:
        print("使い方: python compare_images_phash.py <画像URL1> <画像URL2>")
        print("例: python compare_images_phash.py 'https://i.ebayimg.com/...' 'https://i.ebayimg.com/...'")
        sys.exit(1)

    url1, url2 = sys.argv[1], sys.argv[2]
    distance, comment = compare_images(url1, url2)

    if distance < 0:
        print(comment)
        sys.exit(1)

    print(f"ハミング距離: {distance}")
    print(f"判定: {comment}")


if __name__ == "__main__":
    main()
