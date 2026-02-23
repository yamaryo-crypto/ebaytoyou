# パートナー向け Cursor セットアップ手順

経営者のパートナーが、**Cursor を入れた環境**でこの eBay 画像盗用監視ツールを使えるようにする手順です。Cursor はすでにインストール済みであることを前提にしています。

---

## 全体の流れ

1. **コードを取得する**（Git クローン or フォルダ共有）
2. **Cursor でプロジェクトを開く**
3. **Python 環境を整える**（仮想環境・依存パッケージ）
4. **設定と認証情報を渡す**（.env・config.yaml・secrets）
5. **起動して使う**

---

## 1. コードを取得する

### 方法A: GitHub でクローンする（推奨）

リポジトリが GitHub にある場合：

- **プライベートリポジトリ**  
  → 経営者側でパートナーを「Collaborator」に追加してから、パートナーがクローンします。
- **パブリックリポジトリ**  
  → そのままクローンできます。

```bash
# 作業したいフォルダに移動してから
git clone https://github.com/＜ユーザー名＞/ebaytoyou.git
cd ebaytoyou
```

### 方法B: フォルダを共有する

- ZIP で渡す、または Google ドライブ・Dropbox 等でプロジェクトフォルダ一式を共有します。
- **注意**: `.env` や `secrets/` は通常 Git に含まれていないため、別途「4. 設定と認証情報を渡す」で共有する必要があります。

---

## 2. Cursor でプロジェクトを開く

1. Cursor を起動する。
2. **File → Open Folder**（または `Cmd+O` / `Ctrl+O`）で、上で取得した **ebaytoyou フォルダ** を選択する。
3. フォルダが開けば、以降は Cursor 内のターミナルで作業できます。

---

## 3. Python 環境を整える

Cursor の **ターミナル**（`` Ctrl+` `` または メニュー Terminal → New Terminal）を開き、プロジェクトのルートで以下を実行します。

### 3-1. 仮想環境を作成

**Mac / Linux:**
```bash
python3 -m venv .venv
```

**Windows:**
```bash
python -m venv .venv
```

### 3-2. 依存パッケージをインストール

**Mac / Linux:**
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows:**
```bash
.venv\Scripts\activate
pip install -r requirements.txt
```

プロンプトに `(.venv)` が出ていれば有効化できています。

---

## 4. 設定と認証情報を渡す

ツールは次の設定がないと動きません。**経営者側で準備し、安全な方法でパートナーに渡してください。**

| 対象 | 内容 | 渡し方の例 |
|------|------|-------------|
| `.env` | eBay API・Google 等の環境変数 | 1Password / 安全なチャットで値を送り、パートナーが手動で作成 |
| `config.yaml` | 実行オプション（出力先など） | `.env.example` と同様に `config.yaml.example` をコピーして値を編集して渡す |
| `secrets/service_account.json` | Google サービスアカウント鍵（スプレッドシート利用時） | 安全なファイル共有で JSON のみ渡す |

### 4-1. パートナー側でやること

1. **`.env` を作成**
   - プロジェクトルートに `.env` ファイルを新規作成する。
   - 経営者から受け取った値（EBAY_CLIENT_ID, EBAY_CLIENT_SECRET, EBAY_SELLER_USERNAME など）をそのまま貼り付ける。
   - 詳しい項目は **使い方ガイド.md** の「ステップ3: プロジェクトのセットアップ」を参照。

2. **`config.yaml` を作成**
   ```bash
   cp config.yaml.example config.yaml
   ```
   - 必要に応じて経営者から指示された値に書き換える（例: `output_type: "sheets"` や `GOOGLE_SHEETS_ID` の扱い）。

3. **Google スプレッドシートを使う場合**
   - `secrets` フォルダを作成し、受け取った `service_account.json` を `secrets/service_account.json` として保存する。
   ```bash
   mkdir -p secrets
   # 受け取った JSON を secrets/service_account.json として保存
   ```

### 4-2. 認証のパターン

- **同じ eBay アカウント・同じスプレッドシートで運用する場合**  
  → 経営者と同じ `.env` と `secrets/service_account.json` を共有します。取り扱いには十分注意してください。
- **パートナーが自分の eBay アカウントで使う場合**  
  → パートナー自身が [使い方ガイド.md](../使い方ガイド.md) に沿って、eBay Developer のキー・Refresh Token・必要なら Google 側の設定を用意します。

---

## 5. 起動して使う

Cursor のターミナルで、プロジェクトルートにいる状態で：

```bash
# 仮想環境が有効でない場合（Mac/Linux）
source .venv/bin/activate

# 起動
streamlit run app/web.py
```

または、用意されているスクリプトを使う場合：

```bash
# Mac/Linux
./scripts/start_web.sh
```

ブラウザで **http://localhost:8501** が開けば、ダッシュボード・設定・実行・結果確認ができます。

---

## チェックリスト（パートナー用）

- [ ] コードを取得した（クローン or 共有フォルダ）
- [ ] Cursor でプロジェクトフォルダを開いた
- [ ] `python3 -m venv .venv` と `pip install -r requirements.txt` を実行した
- [ ] `.env` を作成し、必要な値を入れた
- [ ] `config.yaml` を用意した（`config.yaml.example` からコピーして編集）
- [ ] スプレッドシートを使う場合は `secrets/service_account.json` を配置した
- [ ] `streamlit run app/web.py` で起動し、ブラウザで http://localhost:8501 を開けた

---

## 注意事項（経営者・パートナー共通）

- **`.env` と `secrets/` は Git にコミットしないでください。** すでに `.gitignore` で除外されています。
- 認証情報は 1Password や安全なチャットなど、第三者に見られない方法で共有してください。
- 詳しい設定・eBay Developer や Google Cloud の取得方法は **使い方ガイド.md** と **README.md** を参照してください。

---

## トラブル時

- **「streamlit が見つからない」**  
  → ターミナルで `source .venv/bin/activate`（Windows は `.venv\Scripts\activate`）を実行してから `streamlit run app/web.py` を実行してください。
- **「EBAY_CLIENT_ID が設定されていない」**  
  → `.env` がプロジェクトの**ルート**にあり、値が正しく書かれているか確認してください。
- その他は **README.md** の「トラブルシューティング」を参照してください。
