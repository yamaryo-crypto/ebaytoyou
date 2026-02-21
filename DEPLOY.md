# Streamlit Community Cloud デプロイガイド

このガイドでは、eBay 画像盗用監視ツールを **Streamlit Community Cloud** に無料でデプロイし、**GitHub と連携**する手順を説明します。

## 📋 前提条件

- **GitHub アカウント**
- **Streamlit Community Cloud** は GitHub でサインインするため、上記があればその場で連携できます

---

## パート1: GitHub にコードをプッシュする

### 1-1. まだリポジトリがない場合

ターミナルでプロジェクトフォルダに移動し、以下を実行します。

```bash
cd /Users/yamazakiryou/Documents/GitHub/cursor/ebaynisemonotool

# Git が未初期化なら
git init

# デフォルトブランチを main に（任意）
git branch -M main

# 全ファイルをステージ（.gitignore で除外されたものは含まれない）
git add .

# 初回コミット
git commit -m "Initial commit: eBay 画像盗用監視ツール"
```

### 1-2. GitHub でリポジトリを作成

1. https://github.com/new にアクセス
2. **Repository name**: 例）`ebaynisemonotool`
3. **Public** を選択
4. 「Add a README file」等は**不要**（既にローカルにコードがあるため）
5. 「Create repository」をクリック

### 1-3. リモートを追加してプッシュ

GitHub で表示されるコマンドのうち、**既存リポジトリをプッシュする**案内を使います。

```bash
# あなたのユーザー名・リポジトリ名に置き換えてください
git remote add origin https://github.com/あなたのユーザー名/ebaynisemonotool.git

# プッシュ
git push -u origin main
```

- **重要**: `.env`、`config.yaml`、`secrets/` は `.gitignore` に含まれているため、**GitHub にはプッシュされません**（機密情報保護）。

---

## パート2: Streamlit Community Cloud で GitHub 連携・デプロイ

### 2-1. Streamlit Cloud に GitHub でサインイン

1. https://share.streamlit.io にアクセス
2. **「Sign in」** をクリック
3. **「Continue with GitHub」** を選択 → GitHub の認証画面で許可
4. これで **Streamlit と GitHub が連携** した状態になります

### 2-2. アプリをデプロイ

1. ダッシュボードで **「New app」** をクリック
2. 次のように入力：
   - **Repository**: `あなたのユーザー名/ebaynisemonotool`（プッシュしたリポジトリを選択）
   - **Branch**: `main`
   - **Main file path**: `streamlit_app.py`
3. **「Deploy!」** をクリック

初回はビルドに数分かかることがあります。完了すると、`https://xxxxx.streamlit.app` のような URL でアプリにアクセスできます。

### 2-3. 環境変数（Secrets）の設定

デプロイ後、**機密情報は GitHub に含めず**、Streamlit Cloud の Secrets で設定します。

1. ダッシュボードで対象アプリをクリック
2. **「Settings」** → **「Secrets」** を開く
3. 以下の形式で 1 行に 1 つずつ追加：

```
EBAY_CLIENT_ID=あなたのeBay Client ID
EBAY_CLIENT_SECRET=あなたのeBay Client Secret
EBAY_SELLER_USERNAME=あなたのeBayセラーユーザー名
```

4. **「Save」** で保存し、必要に応じて **「Restart app」** でアプリを再起動

---

## 🚀 デプロイ後の運用（参考）

### コードを更新したとき

```bash
git add .
git commit -m "説明メッセージ"
git push origin main
```

Streamlit Community Cloud は **main ブランチの変更を検知**し、自動で再デプロイされます（設定でオフにもできます）。

### 環境変数を追加・変更したとき

- ダッシュボード → 対象アプリ → **Settings** → **Secrets** で編集し、保存後に **Restart app** を実行してください。

---

## 📋 デプロイ設定のまとめ（参照用）

### ステップ1: GitHub リポジトリにプッシュ

- 上記 **パート1** のとおり実施
- **重要**: `.env`、`config.yaml`、`secrets/` は `.gitignore` に含まれているため、プッシュされません（機密情報保護）

### ステップ2: Streamlit Community Cloud にサインアップ

1. https://share.streamlit.io にアクセス
2. 「Sign in」をクリック
3. GitHub アカウントでログイン

### ステップ3: アプリをデプロイ

1. Streamlit Cloud ダッシュボードで「New app」をクリック
2. 以下の情報を入力：
   - **Repository**: あなたの GitHub リポジトリを選択
   - **Branch**: `main` または `master`
   - **Main file path**: `streamlit_app.py`
3. 「Deploy!」をクリック

### ステップ4: 環境変数を設定

デプロイ後、アプリの設定画面で以下の環境変数を設定します：

#### 必須の環境変数

```
EBAY_CLIENT_ID=あなたのeBay Client ID
EBAY_CLIENT_SECRET=あなたのeBay Client Secret
EBAY_SELLER_USERNAME=あなたのeBayセラーユーザー名
```

#### オプションの環境変数

```
EBAY_ENV=production
EBAY_MARKETPLACE_ID=EBAY_US
GOOGLE_SHEETS_ID=スプレッドシートID（使用する場合）
GOOGLE_SERVICE_ACCOUNT_JSON_PATH=./secrets/service_account.json（使用する場合）
HTTP_TIMEOUT_SEC=30
HTTP_RETRY_MAX=3
HTTP_RETRY_BACKOFF_SEC=2
STATE_DB_PATH=/tmp/state.db（デフォルトでOK）
```

**設定方法:**
1. Streamlit Cloud ダッシュボードでアプリを選択
2. 「Settings」→「Secrets」を開く
3. 環境変数を追加（形式: `KEY=VALUE`、1行に1つ）

### ステップ5: Google サービスアカウント JSON（使用する場合）

Google スプレッドシートを使用する場合：

1. サービスアカウント JSON ファイルを準備
2. Streamlit Cloud の「Secrets」で、JSON の内容を環境変数として設定するか、ファイルとしてアップロード

**注意**: `secrets/` フォルダは `.gitignore` に含まれているため、GitHub にはプッシュされません。Streamlit Cloud の Secrets 機能を使用してください。

## ⚠️ 重要な注意事項

### データベースの永続化

Streamlit Community Cloud では、ファイルシステムは**一時的**です。アプリが再起動されると、`data/state.db` は削除される可能性があります。

**対策:**
- 検知結果は CSV ダウンロードまたは Google スプレッドシートに保存することを推奨
- 実行履歴は定期的にエクスポートすることを推奨
- 将来的には外部データベース（SQLite on S3、PostgreSQL など）への移行を検討

### リソース制限

- 無料プランでは、一定時間アクセスがないとアプリがスリープします
- 初回アクセス時に起動に時間がかかる場合があります

### セキュリティ

- `.env` や `config.yaml` は GitHub にプッシュしないでください
- 機密情報は必ず Streamlit Cloud の Secrets 機能を使用してください

## 🔧 トラブルシューティング

### 画面が真っ白な場合

1. **Main file path を変更して試す**  
   Streamlit Cloud のアプリ設定で、**Main file path** を `streamlit_app.py` から **`app/web.py`** に変更し、「Save」→「Reboot app」で再起動してください。  
   （エントリを経由せず `app/web.py` を直接実行すると表示されることがあります。）

2. 上記でも白いままなら、**Manage app** → **Logs** を開いた状態でアプリURLを開き、新しく出たログ（Traceback など）を確認してください。

### アプリが起動しない

1. `requirements.txt` が正しく配置されているか確認
2. `streamlit_app.py` がリポジトリのルートにあるか確認
3. ログを確認（Streamlit Cloud ダッシュボードの「Logs」タブ）

### 環境変数が読み込まれない

1. Secrets に正しく設定されているか確認
2. 変数名が正しいか確認（大文字小文字を区別）
3. アプリを再起動（「Settings」→「Restart app」）

### データベースが消える

- Streamlit Cloud のファイルシステムは一時的です
- 重要なデータは CSV や Google スプレッドシートに保存してください

## 📚 参考リンク

- [Streamlit Community Cloud ドキュメント](https://docs.streamlit.io/deploy/streamlit-community-cloud)
- [環境変数の設定方法](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)
