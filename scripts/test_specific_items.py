#!/usr/bin/env python3
"""
特定の2つのアイテムを比較して、なぜ検知されないのかを確認するスクリプト。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from app.ebay import browse, item_fetcher, auth
from app.match import hashing, matcher
from app.util import http, image

def main() -> None:
    print("=" * 70)
    print("特定アイテムの画像比較テスト")
    print("=" * 70)
    
    # アイテムIDを取得
    your_item_id = "406703657187"
    their_item_id = "317611069586"
    
    print(f"\n自分のアイテム: {your_item_id}")
    print(f"パクっているアイテム: {their_item_id}")
    
    token = auth.get_access_token()
    
    # 自分のアイテムを取得
    print("\n[1] 自分のアイテムを取得中...")
    try:
        seller_username = os.getenv("EBAY_SELLER_USERNAME", "japan-syouzou1000")
        your_item = item_fetcher.fetch_item_by_id(your_item_id, token, search_limit=200, search_sort="newlyListed", seller_username=seller_username)
        if not your_item:
            print("❌ 自分のアイテムが見つかりませんでした")
            sys.exit(1)
        print(f"✅ 取得成功: title={your_item.title[:50] if your_item.title else 'None'}")
        your_image_urls = your_item.image_urls(3)
        print(f"✅ 画像URL数: {len(your_image_urls)}件")
        for i, url in enumerate(your_image_urls[:3], 1):
            print(f"   {i}. {url[:80]}...")
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # パクっているアイテムを取得
    print("\n[2] パクっているアイテムを取得中...")
    try:
        their_item = item_fetcher.fetch_any_item_by_id(their_item_id, token)
        if not their_item:
            print("❌ パクっているアイテムが見つかりませんでした")
            sys.exit(1)
        print(f"✅ 取得成功: title={their_item.title[:50] if their_item.title else 'None'}")
        their_image_urls = their_item.image_urls(3)
        print(f"✅ 画像URL数: {len(their_image_urls)}件")
        for i, url in enumerate(their_image_urls[:3], 1):
            print(f"   {i}. {url[:80]}...")
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # 画像を比較
    print("\n[3] 画像を比較中...")
    max_images = min(len(your_image_urls), len(their_image_urls), 3)
    
    for img_idx in range(max_images):
        print(f"\n--- 画像 {img_idx + 1} の比較 ---")
        your_url = your_image_urls[img_idx]
        their_url = their_image_urls[img_idx]
        
        print(f"自分の画像URL: {your_url[:80]}...")
        print(f"パクっている画像URL: {their_url[:80]}...")
        
        # 画像をダウンロード
        try:
            your_raw = http.download_bytes(your_url)
            their_raw = http.download_bytes(their_url)
            print(f"✅ ダウンロード成功: 自分の画像={len(your_raw)} bytes, パクっている画像={len(their_raw)} bytes")
        except Exception as e:
            print(f"❌ ダウンロード失敗: {e}")
            continue
        
        # ハッシュを計算
        your_sha = hashing.sha256_hex(your_raw)
        their_sha = hashing.sha256_hex(their_raw)
        your_phash = hashing.phash_image(your_raw)
        their_phash = hashing.phash_image(their_raw)
        your_ahash = hashing.ahash_image(your_raw)
        their_ahash = hashing.ahash_image(their_raw)
        your_dhash = hashing.dhash_image(your_raw)
        their_dhash = hashing.dhash_image(their_raw)
        
        print(f"\nハッシュ比較:")
        print(f"  SHA-256一致: {your_sha == their_sha}")
        if your_sha == their_sha:
            print(f"    ✅ SHA-256完全一致！")
        
        # perceptual hashの比較
        phash_threshold = 35
        ahash_threshold = 25
        dhash_threshold = 30
        
        if your_phash and their_phash:
            phash_diff = your_phash - their_phash
            print(f"  pHash差分: {phash_diff} (閾値: {phash_threshold})")
            if phash_diff <= phash_threshold:
                print(f"    ✅ pHash一致（閾値内）")
            else:
                print(f"    ❌ pHash不一致（閾値超過）")
        
        if your_ahash and their_ahash:
            ahash_diff = your_ahash - their_ahash
            print(f"  aHash差分: {ahash_diff} (閾値: {ahash_threshold})")
            if ahash_diff <= ahash_threshold:
                print(f"    ✅ aHash一致（閾値内）")
            else:
                print(f"    ❌ aHash不一致（閾値超過）")
        
        if your_dhash and their_dhash:
            dhash_diff = your_dhash - their_dhash
            print(f"  dHash差分: {dhash_diff} (閾値: {dhash_threshold})")
            if dhash_diff <= dhash_threshold:
                print(f"    ✅ dHash一致（閾値内）")
            else:
                print(f"    ❌ dHash不一致（閾値超過）")
        
        # マッチング判定
        result = matcher.check_match(
            your_sha,
            their_sha,
            our_image_url=your_url,
            their_image_url=their_url,
            also_accept_same_image_url=True,
            our_phash=your_phash,
            their_phash=their_phash,
            our_ahash=your_ahash,
            their_ahash=their_ahash,
            our_dhash=your_dhash,
            their_dhash=their_dhash,
            phash_threshold=phash_threshold,
            ahash_threshold=ahash_threshold,
            dhash_threshold=dhash_threshold,
        )
        
        print(f"\nマッチング結果:")
        print(f"  一致: {result.match}")
        print(f"  証拠: {result.evidence}")
        
        if result.match:
            print(f"  ✅ 検知成功！")
        else:
            print(f"  ❌ 検知失敗")
            print(f"\n  推奨: 閾値を緩和するか、画像の前処理を改善する必要があります")
    
    print("\n" + "=" * 70)
    print("テスト完了")
    print("=" * 70)

if __name__ == "__main__":
    main()
