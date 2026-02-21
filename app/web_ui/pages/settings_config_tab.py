"""設定ページ：設定ファイルタブ。"""
from __future__ import annotations

from typing import Any

import streamlit as st

from app.config import load_config, save_config


def render_config_tab() -> None:
    """設定ファイルタブを描画。"""
    st.markdown("### 設定ファイル編集")
    config = load_config()

    col1, col2 = st.columns(2)
    with col1:
        _render_run_config(config)
    with col2:
        _render_message_config(config)

    if st.button("設定を保存"):
        save_config(config)
        st.success("保存しました！")


def _render_run_config(config: dict[str, Any]) -> None:
    """実行設定を描画。"""
    st.markdown("#### 実行設定")
    st.markdown(
        "**網羅スキャン:** 漏れを減らすには「1回の最大処理出品数」を増やし、"
        "「1画像で1件見つかったら次へ」をオフにしてください。"
    )

    run = config["run"]
    ebay = config.setdefault("ebay", {})

    # プリセットボタン
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📋 標準（速い）を適用"):
            run["max_listings_per_run"] = 200  # 少なめで高速
            run["max_images_per_listing"] = 3
            run["candidates_per_image"] = 50
            run["stop_on_first_match_per_image"] = True
            ebay["search_limit"] = 200
            save_config(config)
            st.rerun()
    with col2:
        if st.button("🔍 網羅スキャンを適用"):
            run["max_listings_per_run"] = 1000
            run["max_images_per_listing"] = 5
            run["candidates_per_image"] = 50
            run["stop_on_first_match_per_image"] = False
            ebay["search_limit"] = 1000
            save_config(config)
            st.rerun()

    run["max_listings_per_run"] = st.number_input(
        "1回の最大処理出品数",
        min_value=40,
        max_value=1000,
        value=max(int(run.get("max_listings_per_run", 1000)), 40),
        help="1回の実行で処理する出品数。全件スキャンするには合計出品数以上に設定。",
    )
    if "search_limit" not in ebay:
        ebay["search_limit"] = 1000
    ebay["search_limit"] = st.number_input(
        "API検索で取得する最大出品数",
        min_value=40,
        max_value=1000,
        value=max(int(ebay.get("search_limit", 1000)), 40),
        help="eBay APIから取得する出品数。全件取得するには合計出品数以上に設定。",
    )
    run["max_images_per_listing"] = st.number_input(
        "1出品あたりの最大画像数",
        min_value=1,
        max_value=20,
        value=run["max_images_per_listing"],
        help="1出品でチェックする画像数。増やすと漏れが少ない。",
    )
    run["candidates_per_image"] = st.number_input(
        "1画像あたりの候補数",
        min_value=10,
        max_value=200,
        value=run["candidates_per_image"],
        help="画像検索で取得する候補数。50以上推奨。",
    )
    run["stop_on_first_match_per_image"] = st.checkbox(
        "1画像で1件見つかったら次へ（オフ=全候補チェック、網羅的）",
        value=run["stop_on_first_match_per_image"],
        help="オフにすると1画像あたり全候補をチェック。時間かかるが漏れが少ない。",
    )
    if "max_concurrent_downloads" not in run:
        run["max_concurrent_downloads"] = 10
    run["max_concurrent_downloads"] = st.number_input(
        "候補画像の並列ダウンロード数",
        min_value=1,
        max_value=50,
        value=run["max_concurrent_downloads"],
        help="同時ダウンロード数。大きいと高速。",
    )


def _render_message_config(config: dict[str, Any]) -> None:
    """メッセージ・出力設定を描画。"""
    st.markdown("#### メッセージ設定")
    config["message"]["deadline_hours"] = st.number_input(
        "期限（時間）",
        min_value=1,
        max_value=168,
        value=config["message"]["deadline_hours"],
    )
    if "output_type" not in config["sheet"]:
        config["sheet"]["output_type"] = "csv"
    config["sheet"]["output_type"] = "csv"
    st.info("📄 検知結果は CSV ファイル（data/detections.csv）に保存されます。")
