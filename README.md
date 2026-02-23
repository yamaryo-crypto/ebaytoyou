# eBay 画像盗用監視ツール

現在出品中（固定価格のみ）の自分の出品画像を起点に、画像が完全一致している他出品を検知し、Googleスプレッドシートへ出力し、送信用メッセージ文面を自動生成するCLIツールです。

## 📋 目次

- [このツールでできること](#このツールでできること)
- [必要なもの](#必要なもの)
- [セットアップ手順](#セットアップ手順)
- [使い方](#使い方)
  - [🌐 ブラウザ版（推奨）](#-ブラウザ版推奨)
  - [💻 コマンドライン版](#-コマンドライン版)
- [設定の詳細](#設定の詳細)
- [出力結果の見方](#出力結果の見方)
- [定期実行の設定](#定期実行の設定)
- [トラブルシューティング](#トラブルシューティング)

---

## このツールでできること

✅ **自動検知**: 自分の出品画像と完全一致する画像を使っている他出品を自動で見つける  
✅ **スプレッドシート出力**: 検知結果を Google スプレッドシートに自動記録  
✅ **メッセージ文面生成**: 相手に送るメッセージの件名・本文を自動生成  
✅ **重複防止**: 同じ検知は2回登録されない  
✅ **週次実行**: 最大100出品ずつ、公平にローテーション処理

## 必要なもの

- **Python 3.11以上**（`python3 --version` で確認）
- **eBay Developer Account**（**必須** - Browse API の Client ID/Secret を取得するため）
- **Google Cloud Project**（**必須** - サービスアカウントと Sheets API 有効化）
- **Google スプレッドシート**（結果を出力する先）

> 💡 **初心者の方へ**: **[使い方ガイド.md](使い方ガイド.md)** を参照してください。eBay Developer、Google Cloud、セットアップからWeb UIでの実行まで、すべて詳しく説明しています。

> 👥 **パートナーに Cursor で使わせる場合**: **[docs/パートナー向けCursorセットアップ手順.md](docs/パートナー向けCursorセットアップ手順.md)** を参照してください。コードの取得・Cursor での開き方・環境構築・認証情報の渡し方までまとめています。

---

## セットアップ手順

### ステップ1: リポジトリをクローンまたはダウンロード

```bash
cd /path/to/your/workspace
# 既にプロジェクトフォルダがある場合はその中で作業
```

### ステップ2: 仮想環境を作成

```bash
python3 -m venv .venv
```

**Windows の場合:**
```bash
python -m venv .venv
```

### ステップ3: 仮想環境を有効化

**Mac/Linux:**
```bash
source .venv/bin/activate
```

**Windows:**
```bash
.venv\Scripts\activate
```

有効化されると、プロンプトの前に `(.venv)` が表示されます。

### ステップ4: 依存パッケージをインストール

```bash
pip install -r requirements.txt
```

### ステップ5: eBay API の設定を取得

1. [eBay Developers Program](https://developer.ebay.com/) にログイン
2. 「My Account」→「Keys」で **Client ID** と **Client Secret** を取得
3. **Application access token** が使えることを確認（Browse API 用）

### ステップ6: Google サービスアカウントを作成

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成
2. 「APIとサービス」→「ライブラリ」で「Google Sheets API」を有効化
3. 「認証情報」→「認証情報を作成」→「サービスアカウント」を選択
4. サービスアカウント名を入力して作成
5. 作成したサービスアカウントをクリック→「キー」タブ→「キーを追加」→「JSON」を選択
6. ダウンロードした JSON ファイルを `./secrets/service_account.json` に保存

### ステップ7: Google スプレッドシートを準備

1. 新しい Google スプレッドシートを作成
2. スプレッドシートの URL から **スプレッドシートID** を取得
   - 例: `https://docs.google.com/spreadsheets/d/1a2b3c4d5e6f7g8h9i0j/edit`
   - この場合、ID は `1a2b3c4d5e6f7g8h9i0j`
3. スプレッドシートをサービスアカウントのメールアドレスに「編集者」権限で共有
   - サービスアカウントのメールは JSON ファイル内の `client_email` に記載されています

### ステップ8: 設定ファイルを作成

#### `.env` ファイル

```bash
cp .env.example .env
```

`.env` を開いて、以下の値を入力してください：

```env
# eBay API 設定（必須）
EBAY_CLIENT_ID=あなたのClient_ID
EBAY_CLIENT_SECRET=あなたのClient_Secret
EBAY_MARKETPLACE_ID=EBAY_US
EBAY_SELLER_USERNAME=あなたのeBayユーザー名

# Google Sheets 設定（必須）
GOOGLE_SHEETS_ID=スプレッドシートID
GOOGLE_SERVICE_ACCOUNT_JSON_PATH=./secrets/service_account.json

# HTTP 設定（オプション、デフォルト値でOK）
HTTP_TIMEOUT_SEC=30
HTTP_RETRY_MAX=3
HTTP_RETRY_BACKOFF_SEC=2
```

#### `config.yaml` ファイル

```bash
cp config.yaml.example config.yaml
```

`config.yaml` は基本的にデフォルトのままでOKですが、必要に応じて調整できます（後述の「設定の詳細」を参照）。

---

## 使い方

### 🌐 ブラウザ版（推奨）

**最も簡単で使いやすい方法です！** ブラウザで設定・実行・結果確認がすべてできます。

#### 1. Web UI を起動

```bash
# 仮想環境を有効化（まだの場合）
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Streamlit を起動
streamlit run app/web.py
```

ブラウザが自動的に開き、`http://localhost:8501` でアクセスできます。

#### 2. 画面の使い方

**🏠 ダッシュボード**
- 総実行回数、総検知数、未対応検知数などの統計情報
- 最近の実行履歴を一覧表示

**⚙️ 設定**
- **環境変数タブ**: `.env` ファイルの編集（eBay API、Google Sheets の設定）
- **設定ファイルタブ**: `config.yaml` の編集（処理数、メッセージ設定など）

**▶️ 実行**
- ドライラン/本番実行の選択
- 特定アイテムのみの実行も可能
- 実行ログをリアルタイムで確認

**📊 結果確認**
- 検知結果一覧（侵害セラー、出品URL、ステータスなど）
- 実行履歴の詳細
- Google スプレッドシートへの直接リンク

#### 3. 実行手順

1. **設定画面**で `.env` と `config.yaml` を確認・編集
2. **実行画面**で「実行開始」ボタンをクリック
3. 実行中はログが表示され、完了すると結果が更新されます
4. **結果確認画面**で検知結果を確認

---

### 💻 コマンドライン版

CLI で実行したい場合や、サーバーで定期実行する場合に使用します。

#### 初回確認: ドライラン

まず、設定が正しいか確認するためにドライランを実行します：

```bash
python -m app.main --once --dry-run
```

**期待される出力:**
```
2026-02-04 15:26:02 [INFO] main: dry-run: run_id=20260204062602, only_item=None
2026-02-04 15:26:02 [INFO] main: dry-run: would get token, search my listings, select up to 100 listings
2026-02-04 15:26:02 [INFO] main: run_summary run_id=20260204062602 scanned_listings=0 scanned_images=0 candidates_checked=0 detections_new=0 errors=0 notes=dry-run
```

エラーが出なければ設定は正しいです！

#### 本番実行（1回）

```bash
python -m app.main --once
```

**実行中に表示される情報:**
- 処理中の出品数
- スキャンした画像数
- チェックした候補数
- 新規検知数
- エラー数

**実行後:**
- `data/state.db` が作成されます（SQLite データベース）
- Google スプレッドシートの `detections` シートに検知結果が追加されます

#### 特定アイテムのみテスト実行

結合テスト用に、特定のアイテムIDだけを処理できます：

```bash
python -m app.main --once --only-item 406614589361
```

---

## 設定の詳細

### `config.yaml` の主要設定項目

| 項目 | 説明 | デフォルト |
|------|------|-----------|
| `run.max_listings_per_run` | 1回の実行で処理する最大出品数 | 100 |
| `run.max_images_per_listing` | 1出品あたり検索に使う最大画像数 | 3 |
| `run.candidates_per_image` | 1画像あたり取得する候補数 | 50 |
| `run.stop_on_first_match_per_image` | 1画像で1件見つかったら次の画像へ | true |
| `sheet.worksheet_name` | スプレッドシートのシート名 | "detections" |
| `sheet.image_preview_formula` | 画像プレビューに `=IMAGE()` を使う | true |
| `message.deadline_hours` | メッセージの期限（時間） | 24 |

**推奨設定（処理時間を短縮したい場合）:**
```yaml
run:
  max_images_per_listing: 3  # 主画像+追加2枚のみ（デフォルト）
```

**より厳密に検知したい場合:**
```yaml
run:
  max_images_per_listing: 15  # 全画像をチェック（処理時間が長くなります）
```

---

## 出力結果の見方

### Google スプレッドシート

`detections` シートに以下の列で結果が記録されます：

| 列名 | 説明 |
|------|------|
| `detected_at` | 検知日時（UTC） |
| `your_item_id` | あなたの出品ID |
| `your_item_url` | あなたの出品URL |
| `infringing_seller_display` | 侵害しているセラーの表示名 |
| `infringing_item_url` | 侵害している出品のURL |
| `infringing_item_id` | 侵害している出品ID |
| `infringing_image_preview` | 侵害画像のプレビュー（`=IMAGE()` 関数） |
| `match_evidence` | 一致証拠（`sha256` / `url` / `both`） |
| `message_subject` | 送信用件名 |
| `message_body` | 送信用本文 |
| `status` | ステータス（`NEW` = 未送信） |

### SQLite データベース（`data/state.db`）

SQLite ブラウザ（例: [DB Browser for SQLite](https://sqlitebrowser.org/)）で開くと、以下のテーブルを確認できます：

- **`runs`**: 実行履歴
- **`listings_scan_state`**: 各出品のスキャン状態
- **`detections`**: 検知履歴（重複防止用）

### ログ出力

実行終了時に以下のようなサマリが表示されます：

```
2026-02-04 15:30:00 [INFO] main: run_summary run_id=20260204063000 scanned_listings=100 scanned_images=300 candidates_checked=1500 detections_new=3 errors=0 notes=(none)
```

- `scanned_listings`: 処理した出品数
- `scanned_images`: スキャンした画像数
- `candidates_checked`: チェックした候補数
- `detections_new`: 新規検知数
- `errors`: エラー数

---

## 定期実行の設定

### cron を使う場合（Mac/Linux）

```bash
crontab -e
```

以下の行を追加（パスは実際のプロジェクトパスに変更）：

```cron
# 週1回 月曜 15:00 JST に実行
0 15 * * 1  cd /path/to/ebay-image-theft-monitor && /path/to/.venv/bin/python -m app.main --once >> logs/run.log 2>&1
```

**サーバが UTC の場合（15:00 JST = 06:00 UTC）:**
```cron
0 6 * * 1  cd /path/to/ebay-image-theft-monitor && /path/to/.venv/bin/python -m app.main --once >> logs/run.log 2>&1
```

### GitHub Actions を使う場合

`.github/workflows/run-weekly.yml` を作成：

```yaml
name: Weekly Scan
on:
  schedule:
    - cron: '0 6 * * 1'  # 月曜 06:00 UTC (15:00 JST)
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python -m app.main --once
        env:
          EBAY_CLIENT_ID: ${{ secrets.EBAY_CLIENT_ID }}
          EBAY_CLIENT_SECRET: ${{ secrets.EBAY_CLIENT_SECRET }}
          # ... 他の環境変数も secrets に設定
```

---

## トラブルシューティング

### ❌ OAuth 認証エラー

**症状:**
```
ValueError: EBAY_CLIENT_ID and EBAY_CLIENT_SECRET must be set
```
または
```
401 Unauthorized
```

**解決方法:**
1. `.env` ファイルに `EBAY_CLIENT_ID` と `EBAY_CLIENT_SECRET` が正しく設定されているか確認
2. eBay Developers で Client ID/Secret が有効か確認
3. `.env` ファイルがプロジェクトルートにあるか確認

### ❌ Google Sheets への書き込みエラー

**症状:**
```
googleapiclient.errors.HttpError: 403 Forbidden
```

**解決方法:**
1. サービスアカウントの JSON ファイルが `./secrets/service_account.json` にあるか確認
2. スプレッドシートをサービスアカウントのメールアドレスに「編集者」権限で共有しているか確認
3. Google Sheets API が有効化されているか確認

### ❌ search_by_image が動かない

**症状:**
```
400 Bad Request: Invalid image
```

**解決方法:**
- `search_by_image` は **Sandbox 環境では動作しません**。本番環境（`EBAY_ENV=production`）で実行してください。
- 画像が WebP などの場合、自動で JPEG に変換されますが、それでもエラーが出る場合はその画像をスキップして続行します。

### ❌ 画像ダウンロードエラー

**症状:**
```
requests.exceptions.RequestException: 403 Forbidden
```

**解決方法:**
- 一部の画像はアクセス制限がある場合があります。その画像はスキップされ、ジョブは続行されます。
- エラーが多い場合は `HTTP_RETRY_MAX` を増やしてください（`.env` で設定）。

### ✅ 正常に動作しているかの確認

1. **ドライランが成功する**
   ```bash
   python -m app.main --once --dry-run
   ```

2. **`data/state.db` が作成される**
   ```bash
   ls -lh data/state.db
   ```

3. **スプレッドシートに行が追加される**（検知があった場合）

4. **ログに run_summary が表示される**
   - `errors=0` なら正常です

---

## よくある質問

### Q: 1回の実行で何件処理されますか？

A: デフォルトで最大100出品です。`config.yaml` の `run.max_listings_per_run` で変更できます。

### Q: 同じ検知が2回登録されませんか？

A: いいえ。SQLite で `your_item_id × infringing_item_id` の組み合わせが UNIQUE 制約になっているため、同じ検知は1回だけ登録されます。

### Q: 処理時間はどのくらいかかりますか？

A: 100出品 × 3画像 × 50候補 = 最大15,000件の画像照合が必要です。API レート制限とネットワーク速度に依存しますが、30分〜2時間程度が目安です。

### Q: メッセージは自動送信されますか？

A: いいえ。v1.0 では自動送信は行いません。スプレッドシートに生成された `message_subject` と `message_body` をコピーして、手動で送信してください。

### Q: オークション出品も監視対象にできますか？

A: 現在は固定価格（FIXED_PRICE）のみです。オークションを含める場合は `app/ebay/browse.py` の `search_my_fixed_price_listings` 関数を修正してください。

---

## サポート

詳細な仕様は `SPEC.md` を参照してください。

問題が解決しない場合は、以下を確認してください：
- Python バージョン（3.11以上）
- すべての依存パッケージがインストールされているか（`pip list`）
- `.env` と `config.yaml` の設定が正しいか
- ログファイル（`logs/run.log`）のエラーメッセージ
