"""設定ページ。"""
from __future__ import annotations

import streamlit as st

from app.web_ui.pages.settings_config_tab import render_config_tab
from app.web_ui.pages.settings_env_tab import render_env_tab


def render_settings() -> None:
    """設定ページを描画。"""
    st.title("⚙️ 設定")
    st.info(
        "🔧 初めて使う場合は、まずここでeBay APIの設定を入力してください。"
        "検知結果はCSVでダウンロードできます。"
    )
    tab1, tab2 = st.tabs(["環境変数 (.env)", "設定ファイル (config.yaml)"])

    with tab1:
        render_env_tab()
    with tab2:
        render_config_tab()
