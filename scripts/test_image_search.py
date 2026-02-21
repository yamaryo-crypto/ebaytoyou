#!/usr/bin/env python3
"""
画像検索のテストスクリプト。
1つの出品の画像をダウンロードして、search_by_imageを実行し、エラーを確認。
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

from app.ebay import browse, auth
from app.util import http, image

def main() -> None:
    print("=" * 70)
    print("画像検索テスト")
    print("=" * 70)
    
    # 1つの出品を取得
    seller_username = os.getenv("EBAY_SELLER_USERNAME", "japan-syouzou1000")
    print(f"\nセラー: {seller_username}")
    print("出品を1件取得中...")
    
    try:
        resp = browse.search_my_fixed_price_listings(
            seller_username, limit=1, offset=0, marketplace_id="EBAY_US"
        )
        items = resp.item_summaries
        if not items:
            print("❌ 出品が見つかりませんでした")
            sys.exit(1)
        
        item = items[0]
        print(f"✅ 出品取得: item_id={item.item_id}, title={item.title[:50] if item.title else 'None'}")
        
        # 画像URLを取得
        image_urls = item.image_urls(1)
        if not image_urls:
            print("❌ 画像URLが見つかりませんでした")
            sys.exit(1)
        
        img_url = image_urls[0]
        print(f"✅ 画像URL: {img_url[:100]}...")
        
        # 画像をダウンロード
        print("\n画像をダウンロード中...")
        try:
            raw = http.download_bytes(img_url)
            print(f"✅ 画像ダウンロード成功: {len(raw)} bytes")
        except Exception as e:
            print(f"❌ 画像ダウンロード失敗: {e}")
            sys.exit(1)
        
        # Base64に変換
        print("\n画像をBase64に変換中...")
        try:
            image_b64 = image.to_base64_for_search(raw)
            if not image_b64:
                print("❌ Base64変換失敗")
                sys.exit(1)
            print(f"✅ Base64変換成功: {len(image_b64)} 文字")
        except Exception as e:
            print(f"❌ Base64変換失敗: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        # 画像検索を実行
        print("\n画像検索を実行中...")
        try:
            token = auth.get_access_token()
            print(f"✅ Access Token取得成功: {len(token)} 文字")
            
            search_resp = browse.search_by_image(
                image_b64,
                limit=10,
                offset=0,
                marketplace_id="EBAY_US",
            )
            print(f"✅ 画像検索成功: 候補数={len(search_resp.item_summaries)}件, 総件数={search_resp.total}件")
            
            if search_resp.item_summaries:
                print("\n候補の最初の3件:")
                for i, candidate in enumerate(search_resp.item_summaries[:3], 1):
                    print(f"  {i}. item_id={candidate.item_id}, title={candidate.title[:50] if candidate.title else 'None'}")
            
        except Exception as e:
            print(f"❌ 画像検索失敗: {e}")
            import traceback
            traceback.print_exc()
            
            # HTTPエラーの場合は詳細を表示
            if hasattr(e, 'response') and e.response is not None:
                print(f"\nHTTPレスポンス詳細:")
                print(f"  ステータスコード: {e.response.status_code}")
                print(f"  レスポンス本文: {e.response.text[:500]}")
            
            sys.exit(1)
        
        print("\n" + "=" * 70)
        print("✅ テスト成功！")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
