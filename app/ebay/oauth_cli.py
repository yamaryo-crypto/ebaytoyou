"""
User OAuth 認証コード取得用 CLI。
一度だけ実行し、取得した EBAY_USER_REFRESH_TOKEN を .env に追加してください。
"""
from __future__ import annotations

import base64
import os
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional
from urllib.parse import parse_qs, urlparse

import requests
from dotenv import load_dotenv

from app.ebay.user_token import _get_client_credentials
from app.util import http

load_dotenv()

AUTH_URL = "https://auth.ebay.com/oauth2/authorize"
TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SCOPE = "https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/sell.inventory"

_auth_code: Optional[str] = None


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_code
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/callback"):
            qs = parse_qs(parsed.query)
            _auth_code = qs.get("code", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        if _auth_code:
            body = "<html><body><h1>認証成功</h1><p>この画面を閉じてターミナルを確認してください。</p></body></html>".encode("utf-8")
        else:
            body = "<html><body><h1>認証エラー</h1><p>code が取得できませんでした。URL を確認してください。</p></body></html>".encode("utf-8")
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


def run_oauth_flow(port: int = 8080) -> None:
    """
    OAuth 認証フローを実行し、Refresh Token を取得。
    RuName の Auth Accepted URL を http://localhost:{port}/callback に設定してください。
    """
    runame = (os.getenv("EBAY_OAUTH_RUNAME") or "").strip()
    if not runame:
        print("エラー: EBAY_OAUTH_RUNAME を設定してください。")
        print("eBay Developer Portal で RuName を作成し、Auth Accepted URL を")
        print(f"  http://localhost:{port}/callback")
        print("  (または http://localhost:{port}/) に設定してください。")
        return

    cid, _ = _get_client_credentials()
    auth_url = (
        f"{AUTH_URL}?client_id={cid}"
        f"&response_type=code"
        f"&redirect_uri={runame}"
        f"&scope={SCOPE.replace(' ', '%20')}"
    )

    server = HTTPServer(("127.0.0.1", port), _CallbackHandler)
    print(f"\nブラウザが開きます。eBay にログインして認可してください。")
    print(f"localhost:{port} で待機しています...\n")
    webbrowser.open(auth_url)
    server.handle_request()

    code = _auth_code
    if not code:
        print("認証コードを取得できませんでした。RuName の Auth Accepted URL を確認してください。")
        return

    auth = base64.b64encode(f"{cid}:{os.getenv('EBAY_CLIENT_SECRET')}".encode()).decode()
    r = requests.post(
        TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Authorization": f"Basic {auth}"},
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": runame,
        },
        timeout=http.get_timeout_sec(),
    )
    if not r.ok:
        print(f"トークン取得失敗: {r.status_code} {r.text}")
        return

    data = r.json()
    refresh = data.get("refresh_token")
    if not refresh:
        print("refresh_token が応答に含まれていません。")
        return

    print("\n=== 成功: EBAY_USER_REFRESH_TOKEN を .env に追加してください ===\n")
    print(f"EBAY_USER_REFRESH_TOKEN={refresh}")
    print("\n========================================\n")


if __name__ == "__main__":
    run_oauth_flow()
