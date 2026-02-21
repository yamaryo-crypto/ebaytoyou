#!/usr/bin/env python3
"""
特定のアイテムの画像で画像検索を行い、パクっているアイテムが検索結果に含まれるか確認するスクリプト。
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
from app.util import http, image

def main() -> None:
    print("=" * 70)
    print("画像検索APIでパクっているアイテムが検索結果に含まれるか確認")
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
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # 各画像で画像検索を実行
    print("\n[2] 画像検索を実行中...")
    found_in_search = False
    
    for img_idx, img_url in enumerate(your_image_urls[:3], 1):
        print(f"\n--- 画像 {img_idx} で検索 ---")
        print(f"画像URL: {img_url[:80]}...")
        
        # 画像をダウンロード
        try:
            raw = http.download_bytes(img_url)
            print(f"✅ ダウンロード成功: {len(raw)} bytes")
        except Exception as e:
            print(f"❌ ダウンロード失敗: {e}")
            continue
        
        # Base64に変換
        try:
            image_b64 = image.to_base64_for_search(raw)
            print(f"✅ Base64変換成功")
        except Exception as e:
            print(f"❌ Base64変換失敗: {e}")
            continue
        
        # 画像検索を実行
        try:
            search_resp = browse.search_by_image(
                image_b64,
                limit=50,
                offset=0,
                marketplace_id="EBAY_US",
            )
            print(f"✅ 検索成功: {len(search_resp.item_summaries)}件の候補が見つかりました")
            
            # パクっているアイテムが検索結果に含まれているか確認
            for candidate in search_resp.item_summaries:
                # レガシーIDで比較
                candidate_legacy_id = candidate.item_id
                if "|" in candidate_legacy_id:
                    parts = candidate_legacy_id.split("|")
                    if len(parts) >= 2:
                        candidate_legacy_id = parts[1]
                
                if candidate_legacy_id == their_item_id or candidate.item_id == their_item_id:
                    print(f"\n🎯 発見！パクっているアイテムが検索結果に含まれています！")
                    print(f"   候補ID: {candidate.item_id}")
                    print(f"   タイトル: {candidate.title[:60] if candidate.title else 'None'}")
                    found_in_search = True
                    break
            
            if not found_in_search:
                print(f"   ❌ パクっているアイテム（{their_item_id}）は検索結果に含まれていません")
                print(f"   検索結果の最初の5件:")
                for i, cand in enumerate(search_resp.item_summaries[:5], 1):
                    cand_id = cand.item_id
                    if "|" in cand_id:
                        parts = cand_id.split("|")
                        if len(parts) >= 2:
                            cand_id = parts[1]
                    print(f"     {i}. ID={cand_id}, title={cand.title[:40] if cand.title else 'None'}")
        except Exception as e:
            print(f"❌ 画像検索失敗: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print("\n" + "=" * 70)
    if found_in_search:
        print("✅ パクっているアイテムが画像検索結果に含まれています")
        print("   画像マッチングの閾値を調整すれば検知できるはずです")
    else:
        print("❌ パクっているアイテムが画像検索結果に含まれていません")
        print("   画像検索APIがリサイズ・加工された画像を検出できていない可能性があります")
        print("   キーワード検索や疑わしいアイテムモードを使用する必要があります")
    print("=" * 70)

if __name__ == "__main__":
    main()
