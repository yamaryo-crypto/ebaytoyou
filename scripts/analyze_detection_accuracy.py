#!/usr/bin/env python3
"""
検知結果の精度分析スクリプト。
正しい検知と誤検知のハッシュ差分を分析して、最適な閾値を決定する。
"""
from __future__ import annotations

import csv
import os
import sys
from pathlib import Path
from typing import Optional

# プロジェクトルートをパスに追加
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from app.store import db
from app.store import repo_detections as repo
from app.match import hashing
from app.util import http

def main() -> None:
    print("=" * 70)
    print("検知結果の精度分析")
    print("=" * 70)
    
    # 正しい検知と誤検知のID
    correct_ids = [119, 125, 126, 132]
    incorrect_ids = [117, 118, 120, 121, 122, 123, 124, 127, 128, 129, 130, 131, 134]
    
    print(f"\n正しい検知: {correct_ids}")
    print(f"誤検知: {incorrect_ids}")
    
    conn = db.get_connection()
    db.init_schema(conn)
    
    # 正しい検知のハッシュ差分を分析
    print("\n" + "=" * 70)
    print("正しい検知のハッシュ差分分析")
    print("=" * 70)
    correct_diffs = {"phash": [], "ahash": [], "dhash": []}
    
    for detection_id in correct_ids:
        detection = repo.get_detection(conn, detection_id)
        if not detection:
            print(f"⚠️  ID {detection_id} が見つかりません")
            continue
        
        diff = analyze_detection(conn, detection)
        if diff:
            correct_diffs["phash"].append(diff.get("phash"))
            correct_diffs["ahash"].append(diff.get("ahash"))
            correct_diffs["dhash"].append(diff.get("dhash"))
            print(f"\nID {detection_id}:")
            print(f"  pHash差分: {diff.get('phash', 'N/A')}")
            print(f"  aHash差分: {diff.get('ahash', 'N/A')}")
            print(f"  dHash差分: {diff.get('dhash', 'N/A')}")
    
    # 誤検知のハッシュ差分を分析
    print("\n" + "=" * 70)
    print("誤検知のハッシュ差分分析")
    print("=" * 70)
    incorrect_diffs = {"phash": [], "ahash": [], "dhash": []}
    
    for detection_id in incorrect_ids:
        detection = repo.get_detection(conn, detection_id)
        if not detection:
            print(f"⚠️  ID {detection_id} が見つかりません")
            continue
        
        diff = analyze_detection(conn, detection)
        if diff:
            incorrect_diffs["phash"].append(diff.get("phash"))
            incorrect_diffs["ahash"].append(diff.get("ahash"))
            incorrect_diffs["dhash"].append(diff.get("dhash"))
            print(f"\nID {detection_id}:")
            print(f"  pHash差分: {diff.get('phash', 'N/A')}")
            print(f"  aHash差分: {diff.get('ahash', 'N/A')}")
            print(f"  dHash差分: {diff.get('dhash', 'N/A')}")
    
    conn.close()
    
    # 統計を計算
    print("\n" + "=" * 70)
    print("統計分析")
    print("=" * 70)
    
    for hash_type in ["phash", "ahash", "dhash"]:
        correct_values = [v for v in correct_diffs[hash_type] if v is not None]
        incorrect_values = [v for v in incorrect_diffs[hash_type] if v is not None]
        
        if not correct_values or not incorrect_values:
            continue
        
        correct_max = max(correct_values)
        incorrect_min = min(incorrect_values)
        
        print(f"\n{hash_type.upper()}:")
        print(f"  正しい検知の最大差分: {correct_max}")
        print(f"  誤検知の最小差分: {incorrect_min}")
        
        if correct_max < incorrect_min:
            optimal_threshold = (correct_max + incorrect_min) // 2
            print(f"  ✅ 最適な閾値: {optimal_threshold} (正しい検知は最大{correct_max}、誤検知は最小{incorrect_min})")
        else:
            print(f"  ⚠️  重複あり: 正しい検知と誤検知が重なっています")
            print(f"     推奨閾値: {correct_max} (正しい検知を優先)")
    
    print("\n" + "=" * 70)
    print("分析完了")
    print("=" * 70)


def analyze_detection(conn, detection) -> Optional[dict]:
    """検知結果の画像をダウンロードしてハッシュ差分を計算。"""
    try:
        # 自分の画像をダウンロード
        our_raw = http.download_bytes(detection.your_image_url)
        our_phash = hashing.phash_image(our_raw)
        our_ahash = hashing.ahash_image(our_raw)
        our_dhash = hashing.dhash_image(our_raw)
        
        # 侵害画像をダウンロード
        their_raw = http.download_bytes(detection.infringing_image_url)
        their_phash = hashing.phash_image(their_raw)
        their_ahash = hashing.ahash_image(their_raw)
        their_dhash = hashing.dhash_image(their_raw)
        
        # 差分を計算
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
    except Exception as e:
        print(f"  ❌ エラー: {e}")
        return None


if __name__ == "__main__":
    main()
