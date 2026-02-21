# ツール設計・制約

## 概要

eBay 画像盗用監視ツールは、自ストアの出品画像が他出品で無断使用されていないかを検知するツールです。

## 処理フロー

1. **出品取得** → 2. **画像スキャン** → 3. **侵害検知** → 4. **出力（CSV / スプレッドシート）**

## 各フェーズの仕様と制約

### 1. 出品取得

**現状の方式**: Browse API `item_summary/search` の `sellers:{セラー名}` フィルタを使用

- **想定用途**: 買い手が「特定セラーの出品を検索」するための API
- **制約**: 自分の出品一覧取得専用 API ではないため、以下の要因で結果が揺らぐ
  - `q`（検索キーワード）: 短いキーワード（例: `a`）だと結果が制限されることがある
  - `deliveryCountry`: 指定すると配送可能国で絞り込み（デフォルトでは無効）
  - インデックス遅延や API 側の制限で、全出品が返らない場合がある

**推奨方式**: Trading API `GetMyeBaySelling`（`EBAY_USER_REFRESH_TOKEN` 設定時）

- セラー自身の出品を確実に取得できる（400 件超も対応）
- User OAuth（Authorization Code）が必要で、一度だけ認証が必要
- `EBAY_USER_REFRESH_TOKEN` を設定すると、Browse API より先に Trading API で出品取得

**複数マーケットプレイス対応**: US をメインに、IT/GB/DE/FR/AU を順に試し、結果をマージして取得

### 2. 画像スキャン

**方式**: Browse API `item_summary/search_by_image`

- 自出品の画像を Base64 にして POST
- eBay の画像類似検索で候補出品（最大 50 件/枚）を取得

### 3. 侵害検知（画像判定）

**方式**: SHA-256 完全一致

- 自画像と候補画像のバイト列を SHA-256 でハッシュ化し比較
- **完全一致のみ**盗用として検知（バイト単位で同一の画像のみ）
- **検知しないもの**: トリミング・リサイズ・圧縮・色変更などの加工済み画像（仕様どおり）

**補助**: 画像 URL が同一の場合も検知対象にできる（`also_accept_same_image_url` オプション）

### 4. 出力

- CSV 出力（デフォルト）
- Google スプレッドシート出力（オプション）
- メッセージ文面（件名・本文）を自動生成

## 安定して動作させるための設定

### 出品数を確実に取得したい場合（推奨）

1. **EBAY_USER_REFRESH_TOKEN** を設定する  
   Trading API GetMyeBaySelling で出品一覧を取得。400 件超でも対応。
   - 取得手順: `python -m app.ebay.oauth_cli` を実行し、eBay にログインして認可
   - 事前に eBay Developer Portal で RuName を作成し、Auth Accepted URL を `http://localhost:8080/callback` に設定
   - `EBAY_OAUTH_RUNAME` に RuName の値を設定

### その他の設定

1. **EBAY_USE_DELIVERY_COUNTRY=0**  
   デフォルトで無効（0 件になるのを避ける）
2. **EBAY_SEARCH_QUERY**  
   必要に応じて検索キーワードを変更（デフォルト: `a`）
3. **複数マーケットプレイス**  
   US に加え IT/GB/DE/FR/AU を常に試し、マージして取得

## トラブルシューティング

| 現象 | 想定原因 | 対処 |
|------|----------|------|
| 0 件しか取れない | `q` や `deliveryCountry` で絞り込みすぎ | `EBAY_USE_DELIVERY_COUNTRY=0`、`EBAY_SEARCH_QUERY=a` を試す |
| 想定より少ない | Browse API の検索結果の制限 | 複数マーケットプレイスでマージ、または Trading API（EBAY_USER_REFRESH_TOKEN）を設定 |
| 加工画像を検知したい | SHA-256 では検知しない設計 | 別の類似度判定（例: perceptual hash）が必要で、現仕様外 |
