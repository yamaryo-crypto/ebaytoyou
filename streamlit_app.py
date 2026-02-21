"""
Streamlit Community Cloud 用エントリーポイント。
app/web.py の内容をそのまま使用。
"""
import sys
from pathlib import Path

# プロジェクトルートをパスに追加（import より前に必須）
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

# 必ず最初にページ設定（Streamlit の仕様）
st.set_page_config(
    page_title="eBay 画像盗用監視ツール",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 最初に1要素表示（白画面対策・読み込み中表示）
st.caption("読み込み中…")

try:
    import app.web
except Exception as e:
    st.error("アプリの読み込みに失敗しました。")
    st.exception(e)
