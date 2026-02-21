#!/usr/bin/env python3
"""
新しい閾値でまだ誤検知されるIDを特定するスクリプト。
"""
from __future__ import annotations

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from app.store import db
from app.store import repo_detections as repo
from app.match import hashing

def main() -> None:
    incorrect_ids = [117, 118, 120, 121, 122, 123, 124, 127, 128, 129, 130, 131, 134]
    
    conn = db.get_connection()
    db.init_schema(conn)
    
    phash_threshold = 20
    ahash_threshold = 15
    dhash_threshold = 22
    
    print("=" * 70)
    print("残っている誤検知の特定")
    print(f"閾値: pHash≤{phash_threshold}, aHash≤{ahash_threshold}, dHash≤{dhash_threshold}")
    print("=" * 70)
    
    remaining = []
    for detection_id in incorrect_ids:
        detection = repo.get_detection(conn, detection_id)
        if not detection:
            continue
        
        if test_detection(detection, phash_threshold, ahash_threshold, dhash_threshold):
            remaining.append(detection_id)
            print(f"\nID {detection_id}: まだ誤検知される")
            # ハッシュ差分を表示
            diff = analyze_detection(detection)
            if diff:
                print(f"  pHash差分: {diff.get('phash')}")
                print(f"  aHash差分: {diff.get('ahash')}")
                print(f"  dHash差分: {diff.get('dhash')}")
    
    conn.close()
    
    print(f"\n残っている誤検知: {remaining} ({len(remaining)}件)")
    print("=" * 70)


def test_detection(detection, phash_threshold: int, ahash_threshold: int, dhash_threshold: int) -> bool:
    """検知結果が新しい閾値でマッチするかテスト。"""
    from app.util import http
    
    try:
        our_raw = http.download_bytes(detection.your_image_url)
        our_phash = hashing.phash_image(our_raw)
        our_ahash = hashing.ahash_image(our_raw)
        our_dhash = hashing.dhash_image(our_raw)
        
        their_raw = http.download_bytes(detection.infringing_image_url)
        their_phash = hashing.phash_image(their_raw)
        their_ahash = hashing.ahash_image(their_raw)
        their_dhash = hashing.dhash_image(their_raw)
        
        match, evidence = hashing.perceptual_match(
            our_phash, their_phash, our_ahash, their_ahash,
            our_dhash=our_dhash, their_dhash=their_dhash,
            phash_threshold=phash_threshold,
            ahash_threshold=ahash_threshold,
            dhash_threshold=dhash_threshold,
        )
        if match:
            print(f"  証拠: {evidence}")
        return match
    except Exception as e:
        print(f"  エラー: {e}")
        return False


def analyze_detection(detection):
    """検知結果の画像をダウンロードしてハッシュ差分を計算。"""
    from app.util import http
    
    try:
        our_raw = http.download_bytes(detection.your_image_url)
        our_phash = hashing.phash_image(our_raw)
        our_ahash = hashing.ahash_image(our_raw)
        our_dhash = hashing.dhash_image(our_raw)
        
        their_raw = http.download_bytes(detection.infringing_image_url)
        their_phash = hashing.phash_image(their_raw)
        their_ahash = hashing.ahash_image(their_raw)
        their_dhash = hashing.dhash_image(their_raw)
        
        phash_diff = None
        ahash_diff = None
        dhash_diff = None
        
        if our_phash and their_phash:
            phash_diff = our_phash - their_phash
        if our_ahash and their_ahash:
            ahash_diff = our_ahash - their_ahash
        if our_dhash and their_dhash:
            dhash_diff = our_dhash - their_dhash
        
        return {
            "phash": phash_diff,
            "ahash": ahash_diff,
            "dhash": dhash_diff,
        }
    except Exception:
        return None


if __name__ == "__main__":
    main()
