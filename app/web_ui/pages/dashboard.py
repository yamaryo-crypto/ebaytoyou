"""ダッシュボードページ。"""
from __future__ import annotations

import streamlit as st

from app.store import db
from app.web_ui.services import get_runs_dataframe


def render_dashboard() -> None:
    """ダッシュボードを描画。"""
    st.title("🏠 ダッシュボード")

    with st.expander("📖 はじめに（初めて使う場合）", expanded=True):
        st.markdown(_INTRO_MARKDOWN)

    st.info("📊 統計情報と実行履歴を確認できます。")
    st.markdown("### 概要")

    conn = db.get_connection()
    db.init_schema(conn)
    total_runs = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    total_detections = conn.execute("SELECT COUNT(*) FROM detections").fetchone()[0]
    new_detections = conn.execute(
        "SELECT COUNT(*) FROM detections WHERE status = 'NEW'"
    ).fetchone()[0]
    last_run = conn.execute(
        "SELECT * FROM runs ORDER BY started_at DESC LIMIT 1"
    ).fetchone()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("総実行回数", total_runs)
    col2.metric("総検知数", total_detections)
    col3.metric("未対応検知", new_detections)
    col4.metric(
        "最終実行",
        last_run["started_at"][:10] if last_run and last_run["started_at"] else "-",
    )

    st.markdown("---")
    st.markdown("### 最近の実行履歴")
    runs_df = get_runs_dataframe()
    if not runs_df.empty:
        st.dataframe(runs_df, use_container_width=True, hide_index=True)
    else:
        st.info("まだ実行履歴がありません。")


_INTRO_MARKDOWN = """
### 🚀 使い方の流れ

1. **⚙️ 設定ページ**で、eBay API の設定を入力
   - `EBAY_CLIENT_ID` と `EBAY_CLIENT_SECRET`（eBay Developer から取得）
   - `EBAY_SELLER_USERNAME`（あなたのeBayユーザー名）

2. **▶️ 実行ページ**で、まず「ドライラン」を実行して動作確認
   - 「ドライラン」にチェックを入れて「実行開始」をクリック
   - エラーが出なければ設定は正しいです！

3. **▶️ 実行ページ**で、本番実行
   - 「ドライラン」のチェックを外して「実行開始」をクリック
   - 処理に数分〜数十分かかります

4. **📊 結果確認ページ**で、検知結果を確認
   - 見つかった検知の一覧が表示されます
   - CSV出力の場合は `data/detections.csv` にメッセージ文面などが保存されます

**詳細は `使い方ガイド.md` を参照してください。**
"""
