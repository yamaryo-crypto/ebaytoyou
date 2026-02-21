#!/usr/bin/env python3
"""
2件の出品を直接比較し、画像盗用の有無を診断。
キーワード検索に候補が含まれるか、ハッシュ比較で検知できるかを確認する。

使用例:
    python scripts/diagnose_pair.py 406703657187 317611069586
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# .env を読み込み
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")


def main() -> None:
    if len(sys.argv) != 3:
        print("使い方: python scripts/diagnose_pair.py <あなたの出品ID> <疑わしい出品ID>")
        print("例: python scripts/diagnose_pair.py 406703657187 317611069586")
        sys.exit(1)

    our_id = sys.argv[1].strip()
    their_id = sys.argv[2].strip()

    print("=" * 60)
    print(f"診断: {our_id} (あなた) vs {their_id} (疑わしい)")
    print("=" * 60)

    # 1) 両方の出品を取得
    from app.ebay import auth, item_fetcher

    token = auth.get_access_token()
    our_item = item_fetcher.fetch_any_item_by_id(our_id, token)
    their_item = item_fetcher.fetch_any_item_by_id(their_id, token)

    if not our_item:
        print(f"エラー: あなたの出品 {our_id} を取得できません")
        sys.exit(1)
    if not their_item:
        print(f"エラー: 疑わしい出品 {their_id} を取得できません")
        sys.exit(1)

    print(f"\n[あなた] {our_item.title or '(タイトルなし)'}")
    print(f"  画像数: {len(our_item.image_urls(24))}")
    print(f"\n[疑わしい] {their_item.title or '(タイトルなし)'}")
    print(f"  画像数: {len(their_item.image_urls(24))}")

    # 2) キーワード検索で 317611069586 が含まれるか確認
    if our_item.title:
        from app.job.processor import _extract_search_keywords, _collect_keyword_candidates
        keywords = _extract_search_keywords(our_item.title)
        print(f"\n[キーワード検索] 抽出キーワード: {keywords}")
        seller = os.getenv("EBAY_SELLER_USERNAME", "japan-syouzou1000")
        kw_cands = _collect_keyword_candidates(our_item.title, our_id, [seller], limit=200)
        cand_item_ids = {c.item_id for c, _ in kw_cands}
        legacy_ids = set()
        for iid in cand_item_ids:
            if "|" in iid:
                parts = iid.split("|")
                if len(parts) >= 2 and parts[1].isdigit():
                    legacy_ids.add(parts[1])
            else:
                legacy_ids.add(iid)
        found_in_search = their_id in legacy_ids or their_id in cand_item_ids
        print(f"  候補数: {len(kw_cands)} 件")
        print(f"  疑わしい出品が候補に含まれる: {'✅ はい' if found_in_search else '❌ いいえ'}")

    # 3) 画像をダウンロードしてハッシュ比較
    from app.util import http
    from app.match import hashing

    our_urls = our_item.image_urls(12)
    their_urls = their_item.image_urls(12)

    print("\n[ハッシュ比較]")
    any_match = False
    for i, our_url in enumerate(our_urls):
        try:
            our_raw = http.download_bytes(our_url)
        except Exception as e:
            print(f"  あなたの画像{i+1}: ダウンロード失敗 - {e}")
            continue
        our_phash = hashing.phash_image(our_raw)
        our_ahash = hashing.ahash_image(our_raw)
        our_dhash = hashing.dhash_image(our_raw)

        for j, their_url in enumerate(their_urls):
            try:
                their_raw = http.download_bytes(their_url)
            except Exception as e:
                continue
            their_phash = hashing.phash_image(their_raw)
            their_ahash = hashing.ahash_image(their_raw)
            their_dhash = hashing.dhash_image(their_raw)

            pd = int(our_phash - their_phash) if our_phash and their_phash else 999
            ad = int(our_ahash - their_ahash) if our_ahash and their_ahash else 999
            dd = int(our_dhash - their_dhash) if our_dhash and their_dhash else 999

            from app.match import matcher
            result = matcher.check_match(
                "", "",
                our_phash=our_phash, their_phash=their_phash,
                our_ahash=our_ahash, their_ahash=their_ahash,
                our_dhash=our_dhash, their_dhash=their_dhash,
            )
            if result.match:
                any_match = True
                print(f"  ✅ マッチ: あなたの画像{i+1} ↔ 疑わしい画像{j+1} (証拠: {result.evidence})")
                print(f"     pHash距離={pd}, aHash距離={ad}, dHash距離={dd}")
            elif pd <= 15 or ad <= 10 or dd <= 10:
                print(f"  ⚠ 近い: あなたの画像{i+1} ↔ 疑わしい画像{j+1}")
                print(f"     pHash距離={pd}, aHash距離={ad}, dHash距離={dd} (閾値外)")

    if not any_match:
        print("  検知されませんでした（マッチなし）")

    print("\n" + "=" * 60)
    if any_match:
        print("→ ハッシュ比較では検知可能です。疑わしいアイテムIDを指定して実行してください。")
    else:
        print("→ ハッシュ距離が閾値を超えているか、キーワード検索に候補が含まれていません。")
    print("=" * 60)


if __name__ == "__main__":
    main()
