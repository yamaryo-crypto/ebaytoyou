# ノートPCでこのツールを動かす手順（GitHub 同期）

このツールは GitHub の **yamaryo-crypto/ebaytoyou** で管理されています。ノートPCでは「クローン → 環境構築 → 設定コピー」で同じように動かせます。

---

## ノートPCで初回セットアップ

### 1. GitHub からクローン

ターミナル（または PowerShell）を開いて、作業したいフォルダに移動してから実行します。

```bash
git clone https://github.com/yamaryo-crypto/ebaytoyou.git
cd ebaytoyou
```

### 2. Python の確認

- **Python 3.11 以上**が必要です。
- 確認: `python3 --version`（Windows の場合は `python --version`）
- 入っていない場合は [python.org](https://www.python.org/) からインストール（Windows では「Add Python to PATH」にチェック）

### 3. 仮想環境を作成して有効化

**Mac / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

プロンプトの先頭に `(.venv)` が出ればOKです。

### 4. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 5. 設定ファイルを用意する

**今の Mac からコピーする方法（推奨）:**

- Mac のプロジェクトフォルダにある **`.env`** と **`config.yaml`** を、USB やクラウドでノートPCにコピーし、**ノートPCの `ebaytoyou` フォルダの直下**に置きます。
- `.env` には eBay の Client ID / Client Secret などが入っています（GitHub には上げていないので、手動でコピーが必要です）。

**ノートPCで一から作る場合:**

- `.env.example` をコピーして `.env` を作り、中身を編集します。
- `config.yaml.example` をコピーして `config.yaml` を作り、必要に応じて編集します。
- eBay の Refresh Token は、ノートPCで初回だけ `scripts/get_new_refresh_token.py` を実行して取得する必要がある場合があります。

### 6. Web UI を起動

```bash
streamlit run app/web.py
```

ブラウザで **http://localhost:8501** が開けば成功です。

---

## 2台目以降の PC で「同期」して使う場合

### Mac（今のPC）で変更したあと

```bash
cd /Users/yamazakiryou/Documents/GitHub/cursor/ebaynisemonotool
git add .
git commit -m "説明メッセージ"
git push origin main
```

### ノートPCで最新を取り込む

```bash
cd ebaytoyou
git pull origin main
```

その後、必要なら `pip install -r requirements.txt` を再度実行し、`streamlit run app/web.py` で起動します。

---

## 注意

- **`.env` と `config.yaml` は GitHub に含まれていません。** 各 PC で手動で用意するか、Mac からコピーしてください。
- ノートPCで eBay の Token エラーが出たら、その PC で `scripts/get_new_refresh_token.py` を実行して新しい Refresh Token を取得してください。

詳細な設定は **使い方ガイド.md** を参照してください。
