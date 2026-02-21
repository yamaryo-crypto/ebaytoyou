#!/usr/bin/env python3
"""
新しい閾値で正しい検知と誤検知がどう判定されるかテストするスクリプト。
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

def test_thresholds(phash_threshold: int, ahash_threshold: int, dhash_threshold: int) -> tuple[int, int]:
    """指定された閾値で正しい検知と誤検知をテスト。"""
    correct_ids = [119, 125, 126, 132]
    incorrect_ids = [117, 118, 120, 121, 122, 123, 124, 127, 128, 129, 130, 131, 134]
    
    conn = db.get_connection()
    db.init_schema(conn)
    
    correct_matches = 0
    incorrect_matches = 0
    
    for detection_id in correct_ids:
        detection = repo.get_detection(conn, detection_id)
        if not detection:
            continue
        if test_detection(detection, phash_threshold, ahash_threshold, dhash_threshold):
            correct_matches += 1
    
    for detection_id in incorrect_ids:
        detection = repo.get_detection(conn, detection_id)
        if not detection:
            continue
        if test_detection(detection, phash_threshold, ahash_threshold, dhash_threshold):
            incorrect_matches += 1
    
    conn.close()
    return correct_matches, incorrect_matches


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
        
        match, _ = hashing.perceptual_match(
            our_phash, their_phash, our_ahash, their_ahash,
            our_dhash=our_dhash, their_dhash=their_dhash,
            phash_threshold=phash_threshold,
            ahash_threshold=ahash_threshold,
            dhash_threshold=dhash_threshold,
        )
        return match
    except Exception:
        return False


def main() -> None:
    print("=" * 70)
    print("新しい閾値のテスト")
    print("=" * 70)
    
    # 複数の閾値の組み合わせをテスト
    test_cases = [
        (20, 15, 22),  # 現在の設定
        (20, 12, 22),  # aHashをより厳しく
        (18, 12, 20),  # すべてをより厳しく
        (22, 15, 24),  # すべてを少し緩く
    ]
    
    for phash_th, ahash_th, dhash_th in test_cases:
        correct, incorrect = test_thresholds(phash_th, ahash_th, dhash_th)
        precision = correct / (correct + incorrect) * 100 if (correct + incorrect) > 0 else 0
        recall = correct / 4 * 100  # 正しい検知は4件
        
        print(f"\n閾値: pHash≤{phash_th}, aHash≤{ahash_th}, dHash≤{dhash_th}")
        print(f"  正しい検知: {correct}/4 ({recall:.1f}%)")
        print(f"  誤検知: {incorrect}/13")
        print(f"  精度: {precision:.1f}%")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
