"""結果確認ページ。"""
from __future__ import annotations

import streamlit as st

from app.config import load_config, load_env
from app.store import db, repo
from app.web_ui.services import get_detections_dataframe, get_runs_dataframe
from app.web_ui.data_queries import get_detection_by_id


def render_results() -> None:
    """結果確認ページを描画。"""
    st.title("📊 結果確認")

    config = load_config()
    output_type = config.get("sheet", {}).get("output_type", "csv")
    if output_type == "csv":
        st.info(
            "🔍 検知結果と実行履歴を確認できます。"
            "CSVダウンロードでは、現在の検知結果一覧に表示されているもの（削除されていないもの）だけがダウンロードされます。"
        )
    else:
        st.info(
            "🔍 検知結果と実行履歴を確認できます。"
            "Google スプレッドシートでも詳細を確認できます。"
        )

    tab1, tab2 = st.tabs(["検知結果", "実行履歴"])

    with tab1:
        _render_detections_tab(output_type)
    with tab2:
        _render_runs_tab()


def _render_detections_tab(output_type: str) -> None:
    """検知結果タブ。"""
    col_title, col_btn = st.columns([3, 1])
    with col_title:
        st.markdown("### 検知結果一覧")
        st.markdown(
            "**見つかった検知の一覧です。** "
            "侵害セラー、出品URL、メッセージ文面などを確認できます。"
        )
    with col_btn:
        if st.button("🔄 更新", help="最新の検知結果を再取得します"):
            st.rerun()

    detections_df = get_detections_dataframe(limit=200)
    if detections_df.empty:
        st.info(
            "まだ検知結果がありません。"
            "実行して検知があった場合、ここに表示されます。"
        )
        return

    # 侵害セラー一覧セクションを追加
    _render_sellers_section(detections_df)

    # 削除用と送信用のチェック列を追加
    if "削除" not in detections_df.columns:
        detections_df.insert(0, "削除", False)
    if "送信" not in detections_df.columns:
        detections_df.insert(1, "送信", False)
    
    # メッセージを含むデータを取得
    detections_with_messages = get_detections_dataframe(limit=200, include_messages=True)
    messages_dict = {}
    if not detections_with_messages.empty and "メッセージ件名" in detections_with_messages.columns:
        for _, row in detections_with_messages.iterrows():
            messages_dict[row["detection_id"]] = {
                "件名": row.get("メッセージ件名", ""),
                "本文": row.get("メッセージ本文", ""),
            }
    
    edited_df = st.data_editor(
        detections_df,
        column_config={
            "削除": st.column_config.CheckboxColumn(
                "削除",
                help="削除する行にチェック",
                default=False,
            ),
            "送信": st.column_config.CheckboxColumn(
                "送信",
                help="メッセージ送信する行にチェック",
                default=False,
            ),
            "detection_id": st.column_config.NumberColumn(
                "ID",
                format="%d",
                disabled=True,
            ),
            "あなたの出品URL": st.column_config.LinkColumn(
                "あなたの出品URL",
                display_text="🔗 開く",
                help="クリックでeBay出品ページへ",
                disabled=True,
            ),
            "侵害出品URL": st.column_config.LinkColumn(
                "侵害出品URL",
                display_text="🔗 開く",
                help="クリックでeBay出品ページへ",
                disabled=True,
            ),
        },
        use_container_width=True,
        hide_index=True,
        key="detections_editor",
    )
    
    # メッセージ送信支援セクション
    selected_for_message = edited_df.loc[edited_df["送信"] == True, "detection_id"].astype(int).tolist()
    if selected_for_message:
        _render_message_sending_section(selected_for_message, messages_dict, edited_df)

    # 検知の削除: 選択削除 / 一括削除
    st.markdown("---")
    st.markdown("### 検知を削除")
    to_delete = edited_df.loc[edited_df["削除"] == True, "detection_id"].astype(int).tolist()
    all_ids = edited_df["detection_id"].astype(int).tolist()
    col_sel, col_all, _ = st.columns([1, 1, 2])
    with col_sel:
        if st.button(
            "🗑️ 選択したものを削除",
            type="secondary",
            help="チェックした行だけ削除します",
            key="delete_detections_selected",
        ):
            if not to_delete:
                st.warning("削除する行をチェックしてください。")
            else:
                conn = db.get_connection()
                try:
                    for did in to_delete:
                        repo.delete_detection(conn, did)
                    st.success(f"{len(to_delete)} 件の検知を削除しました。")
                finally:
                    conn.close()
                st.rerun()
    with col_all:
        if st.button(
            "🗑️ すべて削除",
            type="secondary",
            help="検知結果をすべて削除します",
            key="delete_detections_all",
        ):
            if not all_ids:
                st.warning("削除する検知がありません。")
            else:
                conn = db.get_connection()
                try:
                    for did in all_ids:
                        repo.delete_detection(conn, did)
                    st.success(f"{len(all_ids)} 件すべて削除しました。")
                finally:
                    conn.close()
                st.rerun()

    if output_type == "csv":
        _render_csv_output_section()
    else:
        _render_sheets_output_section()


def _render_sellers_section(detections_df) -> None:
    """侵害セラー一覧セクションを描画。"""
    st.markdown("---")
    col_title, col_btn = st.columns([3, 1])
    with col_title:
        st.markdown("### 👥 侵害セラー一覧")
        st.markdown("**検知された侵害セラーの一覧です。** セラー名をクリックするとeBayのセラーページに移動します。")
    
    # 重複を除いたセラー一覧を取得
    sellers = detections_df["侵害セラー"].dropna().unique().tolist()
    if not sellers:
        st.info("侵害セラーがありません。")
        return
    
    # セラー名とURLのペアを作成
    seller_links = []
    sellers_sorted = sorted(sellers)
    for seller in sellers_sorted:
        # eBayのセラーページURLを生成（usernameまたはuser_idを使用）
        seller_url = f"https://www.ebay.com/usr/{seller}"
        seller_links.append(f"- [{seller}]({seller_url})")
    
    # セラー一覧を表示
    st.markdown("\n".join(seller_links))
    
    # 統計情報
    seller_counts = detections_df["侵害セラー"].value_counts()
    st.caption(f"合計 {len(sellers)} 名のセラー、検知件数: {len(detections_df)} 件")
    
    # CSVダウンロード機能
    with col_btn:
        import io
        import pandas as pd
        
        # CSV用のデータフレームを作成
        sellers_df = pd.DataFrame({
            "セラー名": sellers_sorted,
            "セラーページURL": [f"https://www.ebay.com/usr/{seller}" for seller in sellers_sorted],
            "検知件数": [seller_counts.get(seller, 0) for seller in sellers_sorted],
        })
        
        # CSVとして出力
        csv_buffer = io.StringIO()
        sellers_df.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
        csv_data = csv_buffer.getvalue()
        
        st.download_button(
            "📥 CSV をダウンロード",
            data=csv_data.encode("utf-8-sig"),
            file_name="infringing_sellers.csv",
            mime="text/csv",
            help=f"侵害セラー一覧（{len(sellers)}名）をCSVとしてダウンロードします",
            key="download_sellers_csv",
        )


def _render_csv_output_section() -> None:
    """CSV 出力のセクション。現在の検知結果一覧（削除されていないもの）のみをダウンロード。"""
    import io
    
    st.markdown("---")
    st.markdown("### 📄 CSV ダウンロード")
    st.markdown(
        "**現在の検知結果一覧に表示されているものだけ**をCSVとしてダウンロードできます。"
        "過去に削除した検知結果は含まれません。"
    )
    st.caption("CSVには、メッセージ文面（件名・本文）と侵害セラー一覧も含まれています。Excel等で開いて確認できます。")
    
    # 現在表示されている検知結果（削除されていないもの）を取得（メッセージも含む）
    detections_df = get_detections_dataframe(limit=200, include_messages=True)
    
    if detections_df.empty:
        st.info("ダウンロードできる検知結果がありません。")
        return
    
    # 侵害セラー一覧を追加
    sellers = detections_df["侵害セラー"].dropna().unique().tolist()
    sellers_list = ", ".join(sorted(sellers))
    
    # CSVとして出力
    csv_buffer = io.StringIO()
    # 削除列を除外してCSV出力
    csv_df = detections_df.drop(columns=["削除"], errors="ignore")
    # 侵害セラー一覧列を追加（すべての行に同じ値を設定）
    csv_df["侵害セラー一覧"] = sellers_list
    csv_df.to_csv(csv_buffer, index=False, encoding="utf-8-sig")  # UTF-8 BOM付き（Excel対応）
    csv_data = csv_buffer.getvalue()
    
    st.download_button(
        "📥 CSV をダウンロード",
        data=csv_data.encode("utf-8-sig"),
        file_name="detections.csv",
        mime="text/csv",
        help=f"現在の検知結果一覧（{len(detections_df)}件）をダウンロードします",
    )


def _render_sheets_output_section() -> None:
    """Google Sheets 出力のセクション。"""
    env = load_env()
    sheets_id = env.get("GOOGLE_SHEETS_ID", "")
    if not sheets_id:
        return
    st.markdown("---")
    st.markdown(
        f"### [📊 Google スプレッドシートで詳細を確認する]"
        f"(https://docs.google.com/spreadsheets/d/{sheets_id})"
    )
    st.markdown("スプレッドシートには、メッセージ文面（件名・本文）も含まれています。")


def _render_runs_tab() -> None:
    """実行履歴タブ。"""
    col_title, col_btn = st.columns([3, 1])
    with col_title:
        st.markdown("### 実行履歴")
        st.markdown(
            "**過去の実行結果を確認できます。** "
            "処理した出品数、検知数、エラー数などが表示されます。"
        )
    with col_btn:
        if st.button("🔄 更新", key="refresh_runs", help="最新の実行履歴を再取得します"):
            st.rerun()

    runs_df = get_runs_dataframe()
    if not runs_df.empty:
        if "削除" not in runs_df.columns:
            runs_df.insert(0, "削除", False)
        edited_runs_df = st.data_editor(
            runs_df,
            column_config={
                "削除": st.column_config.CheckboxColumn(
                    "削除",
                    help="削除する行にチェック",
                    default=False,
                ),
                "実行ID": st.column_config.TextColumn("実行ID", disabled=True),
                "開始時刻": st.column_config.TextColumn("開始時刻", disabled=True),
                "終了時刻": st.column_config.TextColumn("終了時刻", disabled=True),
                "処理出品数": st.column_config.NumberColumn("処理出品数", format="%d", disabled=True),
                "スキャン画像数": st.column_config.NumberColumn("スキャン画像数", format="%d", disabled=True),
                "候補チェック数": st.column_config.NumberColumn("候補チェック数", format="%d", disabled=True),
                "新規検知数": st.column_config.NumberColumn("新規検知数", format="%d", disabled=True),
                "エラー数": st.column_config.NumberColumn("エラー数", format="%d", disabled=True),
                "備考": st.column_config.TextColumn("備考", disabled=True),
            },
            use_container_width=True,
            hide_index=True,
            key="runs_editor",
        )

        # 実行履歴の削除: 選択削除 / 一括削除
        st.markdown("---")
        st.markdown("### 実行履歴を削除")
        # edited_runs_df から削除対象を取得（チェックボックスが True の行）
        to_delete_runs = []
        if "削除" in edited_runs_df.columns and "実行ID" in edited_runs_df.columns:
            to_delete_runs = edited_runs_df.loc[edited_runs_df["削除"] == True, "実行ID"].astype(str).tolist()
        all_run_ids = edited_runs_df["実行ID"].astype(str).tolist() if "実行ID" in edited_runs_df.columns else []
        col_sel, col_all, _ = st.columns([1, 1, 2])
        with col_sel:
            if st.button(
                "🗑️ 選択したものを削除",
                key="delete_runs_selected",
                type="secondary",
                help="チェックした実行履歴と紐づく検知を削除します",
            ):
                if not to_delete_runs:
                    st.warning("削除する行をチェックしてください。")
                else:
                    conn = db.get_connection()
                    try:
                        for run_id in to_delete_runs:
                            repo.delete_run(conn, run_id)
                        st.success(f"{len(to_delete_runs)} 件の実行履歴を削除しました。")
                    finally:
                        conn.close()
                    st.rerun()
        with col_all:
            if st.button(
                "🗑️ すべて削除",
                key="delete_runs_all",
                type="secondary",
                help="実行履歴をすべて削除します（紐づく検知も削除）",
            ):
                if not all_run_ids:
                    st.warning("削除する実行履歴がありません。")
                else:
                    conn = db.get_connection()
                    try:
                        for run_id in all_run_ids:
                            repo.delete_run(conn, run_id)
                        st.success(f"{len(all_run_ids)} 件すべて削除しました。")
                    finally:
                        conn.close()
                    st.rerun()
    else:
        st.info(
            "まだ実行履歴がありません。"
            "「▶️ 実行」ページで実行すると、ここに履歴が表示されます。"
        )


def _render_message_sending_section(
    selected_ids: list[int], messages_dict: dict, edited_df
) -> None:
    """メッセージ送信支援セクションを描画。"""
    st.markdown("---")
    st.markdown("### 📧 メッセージ送信支援")
    st.markdown("**選択した検知のメッセージ文面を確認・コピーできます。**")
    
    # セラーごとにグループ化
    seller_groups: dict[str, list[int]] = {}
    for det_id in selected_ids:
        row = edited_df[edited_df["detection_id"] == det_id]
        if not row.empty:
            seller = row.iloc[0]["侵害セラー"]
            if seller not in seller_groups:
                seller_groups[seller] = []
            seller_groups[seller].append(det_id)
    
    for seller, det_ids in seller_groups.items():
        with st.expander(f"📨 {seller} ({len(det_ids)}件)", expanded=True):
            for det_id in det_ids:
                detection_info = get_detection_by_id(det_id)
                if not detection_info:
                    continue
                
                st.markdown(f"**検知ID: {det_id}** | 侵害出品: [{detection_info['侵害出品ID']}]({detection_info['侵害出品URL']})")
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    subject = detection_info.get("メッセージ件名", "")
                    body = detection_info.get("メッセージ本文", "")
                    
                    st.text_area(
                        "件名",
                        value=subject,
                        key=f"subject_{det_id}",
                        height=30,
                        disabled=True,
                    )
                    st.text_area(
                        "本文",
                        value=body,
                        key=f"body_{det_id}",
                        height=150,
                        disabled=True,
                    )
                
                with col2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # 件名コピー
                    st.code(subject, language=None)
                    if st.button("📋 件名をコピー", key=f"copy_subject_{det_id}", use_container_width=True):
                        st.code(subject, language=None)
                        st.success("件名を上記に表示しました。テキストを選択してコピーしてください。")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # 本文コピー
                    st.code(body[:100] + "..." if len(body) > 100 else body, language=None)
                    if st.button("📋 本文をコピー", key=f"copy_body_{det_id}", use_container_width=True):
                        st.code(body, language=None)
                        st.success("本文を上記に表示しました。テキストを選択してコピーしてください。")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # eBayメッセージ送信ページへのリンク
                    seller_username = seller
                    ebay_message_url = f"https://www.ebay.com/messages/compose?recipient={seller_username}"
                    st.markdown(
                        f'<a href="{ebay_message_url}" target="_blank" style="display: inline-block; padding: 0.5rem 1rem; background-color: #0066cc; color: white; text-decoration: none; border-radius: 0.25rem;">📧 eBayでメッセージ送信</a>',
                        unsafe_allow_html=True
                    )
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    # ステータス更新
                    current_status = detection_info.get("ステータス", "NEW")
                    if current_status == "NEW":
                        if st.button("✅ 送信済みにマーク", key=f"mark_sent_{det_id}", use_container_width=True):
                            conn = db.get_connection()
                            try:
                                repo.update_detection_status(conn, det_id, "SENT")
                                st.success("送信済みにマークしました")
                                st.rerun()
                            finally:
                                conn.close()
                    elif current_status == "SENT":
                        st.success("✓ 送信済み")
