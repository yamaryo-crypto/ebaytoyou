"""
Streamlit Web UI エントリーポイント。
ブラウザで設定・実行・結果確認ができる。
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# プロジェクトルートをパスに追加
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv()

from app.web_ui.pages import render_dashboard, render_results, render_run_page, render_settings

# ページ設定
st.set_page_config(
    page_title="eBay 画像盗用監視ツール",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# セッション状態の初期化
if "run_status" not in st.session_state:
    st.session_state.run_status = None
if "run_logs" not in st.session_state:
    st.session_state.run_logs = []
if "run_progress" not in st.session_state:
    st.session_state.run_progress = None
if "last_run_id" not in st.session_state:
    st.session_state.last_run_id = None

_SIDEBAR_GUIDE = """
**初めて使う場合:**
1. 「⚙️ 設定」でeBayの設定を入力
2. 「▶️ 実行」でドライランを実行（動作確認）
3. 問題なければ本番実行
4. 「📊 結果確認」で検知結果を確認

**詳細は `使い方ガイド.md` を参照**
"""

# サイドバー
with st.sidebar:
    # タイトルを1行で表示するためのカスタムCSS
    st.markdown(
        """
        <style>
        .sidebar-title {
            font-size: 0.95rem;
            font-weight: 600;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            line-height: 1.4;
            margin-bottom: 0.5rem;
            padding: 0.25rem 0;
        }
        </style>
        <div class="sidebar-title">🔍 eBay 画像盗用監視</div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")
    page = st.radio(
        "ページ",
        ["🏠 ダッシュボード", "⚙️ 設定", "▶️ 実行", "📊 結果確認"],
    )
    st.markdown("---")
    with st.expander("❓ 使い方ガイド", expanded=False):
        st.markdown(_SIDEBAR_GUIDE)

# ページルーティング
if page == "🏠 ダッシュボード":
    render_dashboard()
elif page == "⚙️ 設定":
    render_settings()
elif page == "▶️ 実行":
    render_run_page()
elif page == "📊 結果確認":
    render_results()
