#!/usr/bin/env python3
"""
Trading API の動作テスト。
User Token が正しく動作しているか、各サイトで何件取得できるかを確認。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# .env を読み込み
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")


def main() -> None:
    seller_username = os.getenv("EBAY_SELLER_USERNAME", "japan-syouzou1000")
    
    print("=" * 70)
    print(f"Trading API テスト: セラー={seller_username}")
    print("=" * 70)
    
    # User Token の確認
    from app.ebay.user_token import get_user_access_token, has_user_refresh_token
    
    if not has_user_refresh_token():
        print("❌ EBAY_USER_REFRESH_TOKEN が設定されていません")
        sys.exit(1)
    
    print("\n[1] User Access Token の取得")
    try:
        user_token = get_user_access_token()
        if not user_token:
            print("❌ User Access Token の取得に失敗しました")
            sys.exit(1)
        print(f"✅ User Access Token 取得成功 (長さ={len(user_token)}文字)")
    except Exception as e:
        print(f"❌ User Access Token 取得エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Trading API のテスト
    print("\n[2] Trading API GetMyeBaySelling のテスト")
    from app.ebay.trading import get_my_ebay_selling_active, SITE_ID_TO_NAME
    
    try:
        items = get_my_ebay_selling_active(
            user_token, seller_username, max_total=1000
        )
        print(f"\n✅ Trading API テスト成功")
        print(f"   取得件数: {len(items)}件")
        
        if len(items) > 0:
            print(f"\n   サンプル出品ID（最初の5件）:")
            for i, item in enumerate(items[:5], 1):
                print(f"   {i}. {item.item_id} - {item.title or '(タイトルなし)'}")
        else:
            print("\n   ⚠️  取得件数が0件です。以下を確認してください:")
            print("   - User Token が正しく設定されているか")
            print("   - セラーユーザー名が正しいか")
            print("   - 実際に出品があるか")
            
    except Exception as e:
        print(f"\n❌ Trading API テスト失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # 各サイトごとの詳細テスト
    print("\n[3] 各サイトごとの詳細テスト")
    from app.ebay.trading import _fetch_my_ebay_selling_one_site
    
    site_ids = [0, 3, 15, 77, 101, 71]  # US, UK, AU, DE, IT, FR
    for site_id in site_ids:
        site_name = SITE_ID_TO_NAME.get(site_id, str(site_id))
        print(f"\n   サイト: SiteID {site_id} ({site_name})")
        try:
            site_items = _fetch_my_ebay_selling_one_site(
                user_token, seller_username, site_id, max_total=10
            )
            print(f"   ✅ 取得成功: {len(site_items)}件")
            if len(site_items) > 0:
                print(f"   サンプル: {site_items[0].item_id}")
        except Exception as e:
            print(f"   ❌ 失敗: {e}")
    
    print("\n" + "=" * 70)
    print("テスト完了")
    print("=" * 70)


if __name__ == "__main__":
    main()
