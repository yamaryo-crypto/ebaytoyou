"""Web UI ページ用の定数・文言。"""
from __future__ import annotations

ENV_GUIDE_MARKDOWN = """
**eBay API の設定:**
1. [eBay Developers Program](https://developer.ebay.com/) にログイン
2. 「My Account」→「Keys」を開く
3. Production で「Create a keyset」をクリック
4. **Client ID** と **Client Secret** をコピー
5. **EBAY_SELLER_USERNAME** には、eBay のあなたのユーザー名を入力（例: japan-syouzou1000）
6. **EBAY_MARKETPLACE_ID**: 監視対象サイト（偽物が多い US→EBAY_US, ebay.it→EBAY_IT）
"""
