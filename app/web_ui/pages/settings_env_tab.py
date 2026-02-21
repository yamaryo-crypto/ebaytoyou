"""設定ページ：環境変数タブ。"""
from __future__ import annotations

import time

import streamlit as st

from app.config import load_env, save_env
from app.constants import DEFAULT_MARKETPLACE_ID
from app.web_ui.pages.constants import ENV_GUIDE_MARKDOWN


def render_env_tab() -> None:
    """環境変数タブを描画。"""
    st.markdown("### 環境変数設定")
    st.markdown(
        "**必須項目:** eBay API の設定を入力してください。"
        "検知結果は CSV ファイルでダウンロードできます。"
    )

    with st.expander("📖 各項目の取得方法", expanded=False):
        st.markdown(ENV_GUIDE_MARKDOWN)

    env = load_env()

    st.markdown("#### 🔴 必須項目")
    col1, col2 = st.columns(2)

    with col1:
        ebay_client_id = st.text_input(
            "EBAY_CLIENT_ID",
            value=env.get("EBAY_CLIENT_ID", ""),
            help="eBay Developer の Client ID（例: YourApp-Prod-XXXX-XXXX）",
            placeholder="YourApp-Prod-XXXX-XXXX",
        )
        ebay_client_secret = st.text_input(
            "EBAY_CLIENT_SECRET",
            value=env.get("EBAY_CLIENT_SECRET", ""),
            type="password",
            help="eBay Developer の Client Secret",
            placeholder="Prod-XXXX-XXXX-XXXX",
        )
        ebay_seller_username = st.text_input(
            "EBAY_SELLER_USERNAME",
            value=env.get("EBAY_SELLER_USERNAME", ""),
            help="あなたのeBayユーザー名（出品者名。例: japan-syouzou1000）。filter=sellers:{セラーID} で検索に使用します。",
            placeholder="japan-syouzou1000",
        )

    with col2:
        ebay_marketplace_id = st.text_input(
            "EBAY_MARKETPLACE_ID",
            value=env.get("EBAY_MARKETPLACE_ID", DEFAULT_MARKETPLACE_ID),
            help="監視対象サイト: 偽物が多い US→EBAY_US, ebay.it→EBAY_IT",
            placeholder="EBAY_US",
        )

    st.markdown("#### ⚪ オプション項目（デフォルト値でOK）")
    col1, col2, col3 = st.columns(3)
    with col1:
        http_timeout = st.number_input(
            "HTTP_TIMEOUT_SEC",
            min_value=10,
            max_value=300,
            value=int(env.get("HTTP_TIMEOUT_SEC", "30")),
            help="HTTP タイムアウト（秒）",
        )
    with col2:
        http_retry_max = st.number_input(
            "HTTP_RETRY_MAX",
            min_value=1,
            max_value=10,
            value=int(env.get("HTTP_RETRY_MAX", "3")),
            help="HTTP リトライ回数",
        )
    with col3:
        http_retry_backoff = st.number_input(
            "HTTP_RETRY_BACKOFF_SEC",
            min_value=1,
            max_value=10,
            value=int(float(env.get("HTTP_RETRY_BACKOFF_SEC", "2"))),
            help="HTTP リトライ間隔（秒）",
        )

    required_fields: dict[str, str] = {
        "EBAY_CLIENT_ID": ebay_client_id,
        "EBAY_CLIENT_SECRET": ebay_client_secret,
        "EBAY_SELLER_USERNAME": ebay_seller_username,
    }
    missing_fields = [k for k, v in required_fields.items() if not v.strip()]
    if missing_fields:
        st.warning(f"⚠️ 以下の必須項目が未入力です: {', '.join(missing_fields)}")

    new_env = {
        "EBAY_CLIENT_ID": ebay_client_id,
        "EBAY_CLIENT_SECRET": ebay_client_secret,
        "EBAY_MARKETPLACE_ID": ebay_marketplace_id,
        "EBAY_SELLER_USERNAME": ebay_seller_username,
        "HTTP_TIMEOUT_SEC": str(http_timeout),
        "HTTP_RETRY_MAX": str(http_retry_max),
        "HTTP_RETRY_BACKOFF_SEC": str(http_retry_backoff),
    }

    if st.button("💾 環境変数を保存", type="primary"):
        if missing_fields:
            st.error("必須項目をすべて入力してください。")
        else:
            save_env(new_env)
            st.success("✅ 保存しました！ページをリロードしてください。")
            time.sleep(1)
            st.rerun()
