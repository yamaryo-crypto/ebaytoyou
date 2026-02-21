"""実行ページ。"""
from __future__ import annotations

import time
from typing import Optional

import streamlit as st

from app.config import load_config
from app.store import db, repo
from app.web_ui.account_verify import verify_account
from app.web_ui.services import run_job_in_thread, sync_job_state_to_session, cancel_job

def render_run_page() -> None:
    """実行ページを描画。"""
    # スレッドの結果を session_state に反映（ScriptRunContext はメインスレッドのみ）
    sync_job_state_to_session()

    st.title("▶️ 実行")
    
    # 実行状態の表示（上部に配置）
    _render_run_status_banner()

    # メイン実行セクション
    st.markdown("---")
    st.markdown("### 🚀 検知処理を実行")
    st.markdown("あなたの出品画像が他出品で無断使用されていないかを検知します。")
    
    # ドライランについての説明
    st.info(
        "💡 **初めて使う場合や設定を変更した後は、「詳細設定」で「ドライラン」にチェックを入れて"
        "動作確認することをおすすめします。** 通常の実行ではチェック不要です。"
    )
    
    config = load_config()
    run_cfg = config.get("run", {})
    ebay_cfg = config.get("ebay", {})

    # 実行オプションは非表示（初心者向けにシンプルに）。デフォルト値を使用
    max_listings = int(run_cfg.get("max_listings_per_run", 1000))
    candidates_per_image = max(int(run_cfg.get("candidates_per_image", 100)), 10)
    search_limit = int(ebay_cfg.get("search_limit", 1000))

    # メイン実行ボタン（大きく目立たせる）
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            "▶️ 実行開始",
            type="primary",
            disabled=st.session_state.run_status == "running",
            use_container_width=True,
            help="検知処理を開始します",
        ):
            overrides = {
                "max_listings_per_run": max_listings,
                "candidates_per_image": candidates_per_image,
                "search_limit": search_limit,
            }
            _handle_run_start(False, False, None, overrides)
    
    # オプション設定（折りたたみ可能）
    with st.expander("⚙️ 詳細設定", expanded=False):
        st.markdown(
            "**ドライランについて:**\n"
            "- 初めて使う時\n"
            "- 設定を変更した後\n"
            "- しばらく使っていなかった時\n"
            "などに動作確認として実行することをおすすめします。通常の実行では不要です。"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            dry_run = st.checkbox(
                "🔍 ドライラン（動作確認用）",
                value=False,
                help="実際にはAPIを呼びません。初回設定確認や動作テストに便利です。",
            )
        with col2:
            only_item_mode = st.checkbox(
                "🎯 特定アイテムのみ",
                value=False,
                help="あなたの出品1件だけを処理します。",
            )
        
        if only_item_mode:
            only_item_id = st.text_input(
                "アイテムID（あなたの出品）",
                value="",
                placeholder="例: 406703657187",
                help="処理したい出品のIDを入力してください",
            )
        else:
            only_item_id = None
        
        col_run, col_verify = st.columns(2)
        with col_run:
            if st.button(
                "実行開始（設定適用）",
                type="primary",
                disabled=st.session_state.run_status == "running",
                use_container_width=True,
            ):
                if only_item_mode and not only_item_id:
                    st.error("アイテムIDを入力してください。")
                else:
                    overrides = {
                        "max_listings_per_run": max_listings,
                        "candidates_per_image": candidates_per_image,
                        "search_limit": search_limit,
                    }
                    _handle_run_start(dry_run, only_item_mode, only_item_id, overrides)
        with col_verify:
            if st.button(
                "🔬 アカウント検証",
                disabled=st.session_state.run_status == "running",
                use_container_width=True,
                help="対象アカウントが正しく検知できるかテストします",
            ):
                _handle_account_verify()

    # 実行ログセクション（常に表示）
    st.markdown("### 実行ログ")
    if st.session_state.run_logs:
        st.caption("実行開始後、このページを開いたままにするとログが表示されます。「出品取得完了: 実際にリストに格納した数」で取得件数を確認できます。")
        log_text = "\n".join(st.session_state.run_logs[-100:])
        st.text_area("ログ", value=log_text, height=400, disabled=True, key="log_area")
    else:
        st.caption("実行ログは「実行開始」ボタンまたは「アカウント検証」ボタンを押すと表示されます。")
        st.text_area("ログ", value="(まだログがありません)", height=200, disabled=True, key="log_area_empty")

    if st.session_state.run_status == "running":
        time.sleep(3)
        st.rerun()


def _render_run_status_banner() -> None:
    """実行状態のバナー表示（ページ上部）。"""
    status = st.session_state.run_status
    progress = st.session_state.get("run_progress")
    
    if status == "running":
        col1, col2 = st.columns([3, 1])
        with col1:
            st.warning("⏳ **実行中...** このページを開いたままにすると進捗が表示されます。")
            if progress and progress.get("total", 0) > 0:
                scanned = progress.get("scanned", 0)
                total = progress.get("total", 0)
                images = progress.get("images_scanned", 0)
                candidates = progress.get("candidates_checked", 0)
                st.caption(
                    f"📊 **{scanned} / {total}** 品目を処理済み "
                    f"（画像 {images} 枚・候補チェック {candidates} 件）"
                )
                st.progress(min(1.0, scanned / total) if total else 0)
        with col2:
            if st.button("⏹️ 中止", type="secondary", use_container_width=True, help="実行中の処理を中止します"):
                cancel_job()
                st.info("中止リクエストを送信しました。処理が停止するまで数秒かかる場合があります。")
                st.rerun()
    elif status == "completed":
        st.success("✅ **実行が完了しました！** 「結果確認」タブで検知結果を確認できます。")
    elif status == "cancelled":
        st.warning("⚠️ **実行が中止されました。** 処理済みの結果は保存されています。")
    elif status == "error":
        st.error("❌ **実行中にエラーが発生しました。** ログを確認してください。")


def _item_id_to_url(item_id: str) -> str:
    """item_id (v1|123|0 形式は中央が数値ID) から eBay 出品URLを生成。"""
    if not item_id or item_id.strip() == "0":
        return "https://www.ebay.com/"
    if "|" in item_id:
        parts = item_id.split("|")
        if len(parts) >= 2 and parts[1].strip().isdigit():
            return f"https://www.ebay.com/itm/{parts[1].strip()}"
    if item_id.strip().isdigit():
        return f"https://www.ebay.com/itm/{item_id.strip()}"
    return "https://www.ebay.com/"


def _handle_account_verify() -> None:
    """アカウント検証を実行して結果を表示。"""
    # 検証中のログをキャプチャするため、stdout/stderrとloggerの両方をキャプチャ
    import logging
    import io
    import sys
    
    # stdout/stderrのキャプチャ
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    
    # loggerのキャプチャ
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S"))
    root = logging.getLogger()
    root.addHandler(handler)
    
    # ログリストを初期化
    if "run_logs" not in st.session_state:
        st.session_state.run_logs = []
    
    try:
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture
        with st.spinner("アカウント検証中..."):
            result = verify_account()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        root.removeHandler(handler)
        
        # すべてのログを収集
        all_logs = []
        stdout_output = stdout_capture.getvalue()
        stderr_output = stderr_capture.getvalue()
        log_output = log_capture.getvalue()
        
        if stdout_output.strip():
            all_logs.extend([line.strip() for line in stdout_output.split("\n") if line.strip()])
        if stderr_output.strip():
            all_logs.extend([line.strip() for line in stderr_output.split("\n") if line.strip()])
        if log_output.strip():
            all_logs.extend([line.strip() for line in log_output.split("\n") if line.strip()])
        
        # 実行ログに追加
        if all_logs:
            st.session_state.run_logs.extend(all_logs[-100:])  # 最新100行まで
    if result.success:
        st.success(result.message)
        if result.sample_item_ids:
            st.markdown("**サンプル出品（クリックで確認）:**")
            urls = result.sample_item_urls or [
                _item_id_to_url(pid) for pid in result.sample_item_ids
            ]
            for item_id, url in zip(result.sample_item_ids[:5], urls[:5]):
                short_id = item_id.split("|")[1] if "|" in item_id else item_id
                st.markdown(f"- [{short_id}]({url})")
    else:
        st.error(result.message)
        if result.sample_item_ids:
            urls = result.sample_item_urls or [
                _item_id_to_url(pid) for pid in result.sample_item_ids
            ]
            st.markdown("**取得したサンプル:**")
            for item_id, url in zip(result.sample_item_ids[:5], urls[:5]):
                short_id = item_id.split("|")[1] if "|" in item_id else item_id
                st.markdown(f"- [{short_id}]({url})")


def _handle_run_start(
    dry_run: bool,
    only_item_mode: bool,
    only_item_id: Optional[str],
    run_overrides: Optional[dict] = None,
) -> None:
    """実行開始ボタンのハンドラ。"""
    if only_item_mode and not only_item_id:
        st.error("アイテムIDを入力してください。")
        return

    # 新しい実行を開始
    st.session_state.run_status = "running"
    st.session_state.run_logs = []
    st.session_state.run_progress = None
    
    run_job_in_thread(
        dry_run,
        only_item_id if only_item_mode else None,
        run_overrides=run_overrides,
    )
    st.info("実行を開始しました。数秒後に自動更新されます。")
    time.sleep(2)
    st.rerun()
