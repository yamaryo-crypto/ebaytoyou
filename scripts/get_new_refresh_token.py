#!/usr/bin/env python3
"""
eBay OAuth Refresh Token を取得するスクリプト。

新しいスコープでRefresh Tokenを取得するには、eBayの認証フローを実行する必要があります。

手順:
1. このスクリプトを実行すると、認証URLが表示されます
2. ブラウザでそのURLを開き、eBayにログインして認証を完了します
3. リダイレクト先のURLから認証コードを取得します
4. 認証コードを入力すると、新しいRefresh Tokenが取得できます
"""
from __future__ import annotations

import base64
import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse, quote

import requests
from dotenv import load_dotenv

# プロジェクトルートをパスに追加
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

# OAuth設定
TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
AUTHORIZE_URL = "https://auth.ebay.com/oauth2/authorize"

# 新しいスコープ
SCOPES = [
    "https://api.ebay.com/oauth/api_scope",
    "https://api.ebay.com/oauth/api_scope/sell.inventory.readonly",
    "https://api.ebay.com/oauth/api_scope/sell.inventory",
]

# リダイレクトURI（eBay OAuthではRuNameを使用）
# eBay OAuthでは標準的なURLではなく、RuNameという特別な値を使用します
# 環境変数 EBAY_OAUTH_RUNAME が設定されていればそれを使用、なければ EBAY_OAUTH_REDIRECT_URI
RUNAME = os.getenv("EBAY_OAUTH_RUNAME")
REDIRECT_URI = RUNAME if RUNAME else os.getenv("EBAY_OAUTH_REDIRECT_URI", "https://auth.ebay.com/oauth2/consent")


def get_client_credentials() -> tuple[str, str]:
    """Client IDとSecretを取得"""
    cid = os.getenv("EBAY_CLIENT_ID")
    secret = os.getenv("EBAY_CLIENT_SECRET")
    if not cid or not secret:
        raise ValueError("EBAY_CLIENT_ID と EBAY_CLIENT_SECRET を .env に設定してください")
    return cid, secret


def build_authorize_url(client_id: str) -> str:
    """認証URLを構築"""
    scope_str = " ".join(SCOPES)
    # eBay OAuthでは redirect_uri にRuNameを使用（URLエンコード不要）
    redirect_param = RUNAME if RUNAME else REDIRECT_URI
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_param,
        "response_type": "code",
        "scope": scope_str,
    }
    # URLエンコーディングを正しく行う（RuNameの場合はそのまま使用）
    if RUNAME:
        # RuNameはURLエンコードしない
        query_string = "&".join([f"{k}={v if k == 'redirect_uri' else quote(str(v), safe='')}" for k, v in params.items()])
    else:
        query_string = "&".join([f"{k}={quote(str(v), safe='')}" for k, v in params.items()])
    return f"{AUTHORIZE_URL}?{query_string}"


def exchange_code_for_token(client_id: str, client_secret: str, auth_code: str) -> dict:
    """認証コードをRefresh Tokenに交換"""
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    scope_str = " ".join(SCOPES)
    # eBay OAuthでは redirect_uri にRuNameを使用
    redirect_param = RUNAME if RUNAME else REDIRECT_URI
    
    r = requests.post(
        TOKEN_URL,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {auth}",
        },
        data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": redirect_param,
            "scope": scope_str,
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def main() -> None:
    print("=" * 70)
    print("eBay OAuth Refresh Token 取得ツール")
    print("=" * 70)
    print()
    
    try:
        client_id, client_secret = get_client_credentials()
    except ValueError as e:
        print(f"❌ エラー: {e}")
        sys.exit(1)
    
    print(f"✅ Client ID: {client_id[:20]}...")
    if RUNAME:
        print(f"✅ RuName (redirect_uri): {RUNAME}")
    else:
        print(f"✅ Redirect URI: {REDIRECT_URI}")
        print("⚠️  注意: EBAY_OAUTH_RUNAME が設定されていません。RuNameを使用することを推奨します。")
    print()
    
    # 認証URLを生成
    auth_url = build_authorize_url(client_id)
    
    print("以下の手順で認証を完了してください:")
    print()
    print("1. 以下のURLをブラウザで開いてください:")
    print()
    print(f"   {auth_url}")
    print()
    print("2. eBayにログインし、アプリの認証を許可してください")
    print()
    print("3. リダイレクト後のURLから認証コードを取得してください")
    if RUNAME:
        print(f"   RuName: {RUNAME}")
        print("   リダイレクト先のURLから認証コード（code=XXXXX）を取得してください")
    else:
        print(f"   リダイレクト先: {REDIRECT_URI}")
    print("   URLの例: https://auth.ebay.com/oauth2/consent?code=XXXXX&expires_in=299")
    print()
    if RUNAME:
        print("   注意: RuNameがDeveloper Consoleで設定したものと一致していることを確認してください")
    else:
        print("   注意: リダイレクトURIがDeveloper Consoleで設定したものと一致していることを確認してください")
    print()
    
    # 認証コードを入力
    auth_code = input("認証コードを入力してください: ").strip()
    
    if not auth_code:
        print("❌ 認証コードが入力されていません")
        sys.exit(1)
    
    print()
    print("認証コードをRefresh Tokenに交換中...")
    
    try:
        token_data = exchange_code_for_token(client_id, client_secret, auth_code)
        
        refresh_token = token_data.get("refresh_token")
        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 7200)
        
        if not refresh_token:
            print("❌ Refresh Tokenが取得できませんでした")
            print(f"レスポンス: {token_data}")
            sys.exit(1)
        
        print()
        print("=" * 70)
        print("✅ Refresh Token 取得成功!")
        print("=" * 70)
        print()
        print("以下のRefresh Tokenを .env ファイルの EBAY_USER_REFRESH_TOKEN に設定してください:")
        print()
        print(f"EBAY_USER_REFRESH_TOKEN={refresh_token}")
        print()
        print("（オプション）Access Token（有効期限: {}秒）:".format(expires_in))
        print(f"EBAY_USER_ACCESS_TOKEN={access_token}")
        print()
        print("=" * 70)
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTPエラー: {e}")
        if e.response is not None:
            print(f"ステータスコード: {e.response.status_code}")
            print(f"レスポンス: {e.response.text}")
            try:
                error_data = e.response.json()
                if "error" in error_data:
                    print(f"\nエラー詳細:")
                    print(f"  error: {error_data.get('error')}")
                    print(f"  error_description: {error_data.get('error_description')}")
            except:
                pass
        print("\nトラブルシューティング:")
        if RUNAME:
            print("1. eBay Developer Consoleで以下のRuNameが設定されているか確認してください:")
            print(f"   {RUNAME}")
            print("2. RuNameが一致しない場合、.env の EBAY_OAUTH_RUNAME を確認してください")
        else:
            print("1. eBay Developer Consoleで以下のリダイレクトURIが設定されているか確認してください:")
            print(f"   {REDIRECT_URI}")
            print("2. .env に EBAY_OAUTH_RUNAME を設定することを推奨します（eBay OAuthではRuNameを使用）")
        print("3. 認証コードが有効期限内（通常5分）であることを確認してください")
        sys.exit(1)
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
