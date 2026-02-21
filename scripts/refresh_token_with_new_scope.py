#!/usr/bin/env python3
"""
既存のRefresh Tokenを使用して、新しいスコープでAccess Tokenを取得するスクリプト。

注意: 既存のRefresh Tokenが古いスコープで発行されている場合、
新しいスコープを要求するとエラーになる可能性があります。
その場合は、get_new_refresh_token.py を使用して新しいRefresh Tokenを取得してください。
"""
from __future__ import annotations

import base64
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

# プロジェクトルートをパスに追加
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"

# 新しいスコープ
SCOPES = [
    "https://api.ebay.com/oauth/api_scope",
    "https://api.ebay.com/oauth/api_scope/sell.inventory.readonly",
    "https://api.ebay.com/oauth/api_scope/sell.inventory",
]


def main() -> None:
    print("=" * 70)
    print("既存のRefresh Tokenで新しいスコープを試す")
    print("=" * 70)
    print()
    
    client_id = os.getenv("EBAY_CLIENT_ID")
    client_secret = os.getenv("EBAY_CLIENT_SECRET")
    refresh_token = os.getenv("EBAY_USER_REFRESH_TOKEN")
    
    if not client_id or not client_secret:
        print("❌ EBAY_CLIENT_ID と EBAY_CLIENT_SECRET を .env に設定してください")
        sys.exit(1)
    
    if not refresh_token:
        print("❌ EBAY_USER_REFRESH_TOKEN が設定されていません")
        print("   新しいRefresh Tokenを取得するには、get_new_refresh_token.py を実行してください")
        sys.exit(1)
    
    print(f"✅ Client ID: {client_id[:20]}...")
    print(f"✅ Refresh Token: {refresh_token[:20]}...")
    print()
    
    scope_str = " ".join(SCOPES)
    print(f"要求するスコープ:")
    for scope in SCOPES:
        print(f"  - {scope}")
    print()
    
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    
    print("Access Tokenを取得中...")
    
    try:
        r = requests.post(
            TOKEN_URL,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {auth}",
            },
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "scope": scope_str,
            },
            timeout=30,
        )
        
        if r.status_code == 200:
            data = r.json()
            access_token = data.get("access_token")
            expires_in = data.get("expires_in", 7200)
            token_type = data.get("token_type", "Bearer")
            scope_returned = data.get("scope", "")
            
            print()
            print("=" * 70)
            print("✅ Access Token 取得成功!")
            print("=" * 70)
            print()
            print(f"Access Token: {access_token[:50]}...")
            print(f"有効期限: {expires_in}秒 ({expires_in // 3600}時間)")
            print(f"Token Type: {token_type}")
            print()
            if scope_returned:
                print("返されたスコープ:")
                for scope in scope_returned.split():
                    print(f"  - {scope}")
            print()
            print("このAccess Tokenは、Trading APIのテストで使用できます。")
            print("=" * 70)
        else:
            print(f"❌ エラー: HTTP {r.status_code}")
            print(f"レスポンス: {r.text}")
            print()
            if r.status_code == 400:
                print("既存のRefresh Tokenが古いスコープで発行されている可能性があります。")
                print("新しいRefresh Tokenを取得するには、get_new_refresh_token.py を実行してください。")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
