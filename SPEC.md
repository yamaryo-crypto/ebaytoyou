version: 1.0
対象セラー: japan-syouzou1000（ebay US）
目的: 現在出品中（固定価格のみ）の自分の出品画像を起点に、盗用（完全一致）している他出品を検知し、Googleスプレッドシートへ出力し、送信用メッセージ文面を自動生成する
備考: eBayへの報告はしない。送信は「文面生成 → 手動コピペ送信」を基本とする

1. 要件確定（あなたの回答を反映）
1-1. 監視対象

eBayサイト: US（Marketplace ID: EBAY_US）

対象: 現在出品中のみ

形式: 固定価格のみ（オークション除外）

Browse API の search は固定価格（FIXED_PRICE）を含む出品がデフォルトで返る

明示的に buyingOptions フィルタで FIXED_PRICE を指定して固定化する（詳細は後述）

1-2. 出品規模と実行制約

現在出品数: 約471

画像枚数: 15枚前後/出品

1回の実行上限: 最大100出品

実行頻度: 週1回

実行時刻: 日本時間15:00

1-3. 判定と候補数

盗用判定: 完全一致のみ

画像検索候補: 1枚あたり上位50件（limit=50）

結果出力: Googleスプレッドシート

必須列: 相手のセラー名 / URL / 画像プレビュー

1-4. メッセージ方針

言語: 日本語

トーン: 強め

期限: 24時間

次の手段: 示唆する（ただし規約違反になる表現は避ける）

送信: 自動送信はしない（文面生成 → 手動送信）

2. 非要件（やらないこと）

eBayへの権利侵害報告（VeRO等）は実装しない

24時間365日の常時監視はしない（週1回ジョブ実行）

画像の「加工一致」（トリミング/圧縮/色変更）対応はしない

eBayメッセージの自動送信は v1.0 では行わない（アカウントリスク・誤検知リスクを避ける）

3. 採用方式（ルート2）概要

自分の現在出品中アイテムをBrowse APIで取得

各アイテムの画像を抽出し、画像をBase64化して search_by_image に投入

返ってきた候補出品の画像と、自分の画像を「完全一致（SHA-256）」で照合

一致したものだけを盗用として採用し、シートへ記録

同時に送信用メッセージ文面を生成してシートへ格納

補足:

search_by_image は Sandbox 非対応（本番環境前提）

4. 技術スタック（Cursor実装を最短にする推奨）
4-1. 言語・実行形態

Python 3.11+

実行: CLIバッチ（週1回 cron / GitHub Actions / Cloud Run のいずれか）

理由:

画像ダウンロード、Base64、SHA-256、HTTP、Sheets API の実装が短い

常駐不要なのでWebサーバ不要

4-2. 永続化（最小）

SQLite（state.db）

既に検知した組み合わせの重複登録を防ぐ

471件を「週1で100件ずつ」公平に回すために「前回処理時刻」を持つ

4-3. 外部API

eBay Browse API

item_summary/search

item_summary/search_by_image

item/getItem（必要時）

Google Sheets API（サービスアカウント推奨）

5. ディレクトリ構成（Cursorにそのまま作らせる）
ebay-image-theft-monitor/
  README.md
  requirements.txt
  .env.example
  config.yaml.example
  app/
    main.py
    ebay/
      auth.py
      browse.py
      models.py
    match/
      hashing.py
      matcher.py
    sheets/
      client.py
      schema.py
    store/
      db.py
      repo.py
    msg/
      templates.py
      generator.py
    util/
      http.py
      log.py
  data/
    state.db            # 実行後に生成
  scripts/
    run_once.sh
    cron_example.txt
  tests/
    test_hashing.py
    test_matcher.py

6. 設定ファイル仕様
6-1. .env（機密情報）
EBAY_ENV=production
EBAY_CLIENT_ID=xxxx
EBAY_CLIENT_SECRET=xxxx

EBAY_MARKETPLACE_ID=EBAY_US
EBAY_SELLER_USERNAME=japan-syouzou1000

GOOGLE_SHEETS_ID=xxxxxxxxxxxxxxxxxxxx
GOOGLE_SERVICE_ACCOUNT_JSON_PATH=./secrets/service_account.json

HTTP_TIMEOUT_SEC=30
HTTP_RETRY_MAX=3
HTTP_RETRY_BACKOFF_SEC=2


OAuthトークンエンドポイント（本番）:

POST https://api.ebay.com/identity/v1/oauth2/token

Client Credentials Grant（Application access token）

6-2. config.yaml（運用設定）
run:
  timezone: "Asia/Tokyo"
  max_listings_per_run: 100
  max_images_per_listing: 3        # v1.0 推奨デフォルト（処理時間短縮）
  candidates_per_image: 50         # あなたの指定
  stop_on_first_match_per_image: true

ebay:
  search_limit: 200                # item_summary/search の1ページ取得数
  search_sort: "newlyListed"       # 任意。安定した順序にしたい場合

match:
  mode: "sha256_exact"             # 完全一致
  also_accept_same_image_url: true # 任意。URL一致も補助証拠にする場合

sheet:
  worksheet_name: "detections"
  append_only: false               # 既存行の更新をするなら false
  image_preview_formula: true      # IMAGE()関数を使う

message:
  language: "ja"
  tone: "strong"
  deadline_hours: 24
  mention_next_steps: true

7. eBay API呼び出し仕様（必須）
7-1. 認証（Application access token）

Client Credentials Grant を使用（Application access token）

token endpoint（本番）

scope は Browse API が要求するものを使用（例: https://api.ebay.com/oauth/api_scope）

7-2. 自分の現在出品中を取得: item_summary/search

GET /buy/browse/v1/item_summary/search

必須ヘッダ

Authorization: Bearer {token}

X-EBAY-C-MARKETPLACE-ID: EBAY_US（USはデフォルトだが明示推奨）

フィルタ（重要）

sellers フィルタ構文: filter=...,sellers:{seller1|seller2}

buyingOptions フィルタ構文: filter=buyingOptions:{AUCTION|FIXED_PRICE}

v1.0で使う具体例（URLエンコードは実装側で行う）:

filter=sellers:{japan-syouzou1000},buyingOptions:{FIXED_PRICE}

補足:

limit と offset でページング（offsetはlimitの倍数制約あり）

7-3. 画像から検索: item_summary/search_by_image

POST /buy/browse/v1/item_summary/search_by_image?limit=50&offset=0&filter=...

本文（JSON）

{"image": "<Base64文字列>"}

Sandbox非対応（本番でのみ動作）

7-4. 画像の抽出元

item_summary/search の response には additionalImages[].imageUrl が含まれる

不足時は GET /buy/browse/v1/item/{item_id} で補完（実装はオプション）

8. 重要な仕様上の注意（セラー名の取得）

出力に「相手のセラー名」を入れたいが、Browse API の seller.username は USユーザーに対して返らないケースがある（2025-09-26以降、一部開発者向け変更）
対策:

seller.username が空なら seller.userId（または類似の不変ID）を出力欄に入れる

シート列名は infringing_seller_display として、どちらが入っても運用できるようにする

9. マッチング仕様（完全一致）
9-1. 完全一致の定義

自分画像（1枚）と候補出品画像（候補の主画像）をそれぞれダウンロード

バイト列で SHA-256 を計算し、ハッシュ一致したら「完全一致」とする

補助証拠（任意）:

画像URL自体が同一の場合も「一致」とみなす（configで切替）

9-2. 検索に使う画像枚数（パフォーマンス）

デフォルト:

max_images_per_listing = 3

先頭3枚（主画像 + 追加画像2枚）

盗用が主画像に集中する前提で、週次運用の処理時間を現実化

設定で 5 や 15 に増やせる（ただし処理時間とAPIコールが増える）

10. データモデル（SQLite）
10-1. tables

listings_scan_state

listing_item_id (PK)

last_scanned_at

last_scanned_run_id

last_scan_status (success/partial/fail)

detections

detection_id (PK)

run_id

detected_at

your_item_id

your_item_url

your_image_index

your_image_url

your_image_sha256

infringing_item_id

infringing_item_url

infringing_seller_display

infringing_image_url

infringing_image_sha256

match_evidence (sha256/url/both)

status (NEW / MESSAGE_READY / SENT / RESOLVED / IGNORE)

message_subject

message_body

runs

run_id (PK)

started_at

finished_at

scanned_listings_count

scanned_images_count

candidates_checked_count

detections_new_count

errors_count

notes

11. Googleスプレッドシート出力仕様
11-1. シート名

detections（configで変更可能）

11-2. 列（必須 + 推奨）

必須（あなたの要望）:

infringing_seller_display

infringing_item_url

infringing_image_preview

運用上必須（重複防止・再現性）:

detected_at

your_item_url

your_item_id

infringing_item_id

match_evidence

送信用:

message_subject

message_body

status

プレビューの作り方:

infringing_image_preview は =IMAGE("<infringing_image_url>") を入れる（configでON/OFF）

11-3. 追記・更新ロジック

v1.0推奨:

新規検知（detectionsに存在しない your_item_id × infringing_item_id）だけを「追記」

status更新はシート側で手動編集しても良い（SENT等）

既存行更新を自動化する場合は、シート読み取り→キーで行更新（実装コスト増）

12. メッセージ生成仕様（日本語・強め・24時間）
12-1. テンプレ（シートへ出す完成文）

subject:

画像使用の停止依頼（24時間以内）

body（プレースホルダ）:

{infringing_item_id}

{deadline_jst}（例: 2026-02-05 15:00 JST）

{your_item_url}（外部リンク扱いになる可能性があるため、本文には入れない設定も可能）

本文（推奨・規約リスク低め）:

貴出品（Item ID: {infringing_item_id}）にて使用されている画像の一部が、当方が撮影・作成した画像と完全一致していることを確認しました。

つきましては、受信から24時間以内（{deadline_jst}）に、該当画像の削除または出品内容の修正をお願いします。
期限までにご対応がない場合、権利保護のための次の対応を検討します。

対応後、このメッセージへ返信でご連絡ください。


注意:

罵倒・脅迫・過剰な制裁宣言・外部連絡先誘導はしない

「次の対応を検討」止まりにする（示唆はするが規約違反になりやすい表現を避ける）

13. ジョブの処理手順（アルゴリズム）
13-1. run開始

run_id を生成（日時ベース）

SQLite に runs を作成

13-2. 対象出品の選定（最大100）

item_summary/search で自分の固定価格出品一覧を取得

listings_scan_state を参照し「最も古くスキャンされたもの」から100件を選ぶ

新規出品（DB未登録）は優先度高（last_scanned_at = null扱い）

13-3. 出品ごとの画像抽出（最大3枚）

primary image を1枚目に

additionalImages から先頭を追加

max_images_per_listing まで採用

13-4. 画像ごとの検索と一致判定

画像1枚につき:

自分画像URLから画像をダウンロード

SHA-256 を計算（your_image_sha256）

Base64 に変換して search_by_image を呼ぶ（limit=50）

返ってきた候補 itemSummaries を上から順に処理

seller が自分自身ならスキップ

候補主画像URLをダウンロード

SHA-256 を計算して一致判定

一致したら detections に登録し、同時に message を生成

stop_on_first_match_per_image=true なら、その画像の候補探索を終了

13-5. 出力

run中に新規検知された detections をシートへ追記

listings_scan_state を更新（success/partial/fail）

runs を更新して終了

14. 失敗時の分岐（必須）
14-1. OAuth失敗

症状:

401/403、token取得失敗

対応:

EBAY_CLIENT_ID / EBAY_CLIENT_SECRET を再確認

本番環境トークンエンドポイントに向いているか確認

scope が Browse API に必要なものを含むか確認

失敗したら即終了（シート更新なし）

14-2. search_by_image が動かない

症状:

Sandboxで実行している

400（imageが不正）

対応:

本番のみ対応であることを確認

ダウンロードした画像が webp 等で失敗する場合:

実装側で JPEG/PNG に変換してからBase64化（Pillow使用）

連続失敗する画像はスキップして次へ（ジョブ全体は止めない）

14-3. 画像ダウンロード失敗（403/404/timeout）

対応:

リトライ（最大3回、指数バックオフ）

それでもダメなら「その画像」だけスキップし、同出品の次画像へ

出品内の全画像が失敗なら listing_scan_state に fail を記録

14-4. Sheets書き込み失敗

対応:

まずローカルSQLiteへの detections 保存は必ず完了させる

Sheets追記が失敗した場合:

ジョブは失敗扱いで終了

次回実行時に「未出力 detections」を優先して出力する（replay機構）

15. コマンド・手順（Cursorで迷わない手順）
15-1. ローカル実行（Mac）

リポジトリ作成

Cursor で新規フォルダ ebay-image-theft-monitor を作成

仮想環境

python3 -m venv .venv
source .venv/bin/activate


依存関係
requirements.txt（例）

requests

python-dotenv

pyyaml

google-api-python-client

google-auth

pillow（画像変換が必要になった時用）

インストール:

pip install -r requirements.txt


設定ファイル

.env.example を .env にコピーし、値を入れる

config.yaml.example を config.yaml にコピーし、値を入れる

GoogleサービスアカウントJSONを ./secrets/service_account.json に置く

スプレッドシートをサービスアカウントのメールアドレスに共有（編集権限）

ドライラン

python -m app.main --once --dry-run


本番1回実行

python -m app.main --once


確認ポイント:

data/state.db が生成される

シートに行が追加される

runサマリがログに出る（scanned_listings_count 等）

15-2. 週1回 15:00 JST の定期実行（cron例）

crontab -e に追加（JSTのサーバで動かす前提）

0 15 * * 1  cd /path/to/ebay-image-theft-monitor && /path/to/.venv/bin/python -m app.main --once >> logs/run.log 2>&1


サーバがUTCの場合は 15:00 JST = 06:00 UTC なので、cron時刻を調整する

16. テスト仕様（最低限）
16-1. ユニットテスト

hashing.py

同一バイト列 → 同一SHA-256

1byte違い → 不一致

matcher.py

sha256一致時のみ match=True

URL一致オプションON/OFFの動作

16-2. 結合テスト（手動）

入力として、あなたが提示した item URL（item_id）をシードにして「1出品だけ処理」モードを作る:

406614589361

406629315533

406617125524

コマンド例:

python -m app.main --once --only-item 406614589361

17. パフォーマンス・API上限設計

Browse API のデフォルト上限は 5,000 calls/day

週1回運用で、1回あたり最大100出品、各出品最大3枚検索なら search_by_image は最大300回

画像照合で候補画像のダウンロードは増えるため、HTTPは並列数を絞る（例: 同時4〜8）

18. 受け入れ条件（完成判定）

週1回実行で、最大100出品のみを処理し、完走する

盗用が見つかった場合のみ、シートに以下が必ず出力される

相手セラー表示（usernameが無い場合は不変IDでも可）

相手出品URL

画像プレビュー

送信用件名・本文

同じ検知が再実行で重複登録されない（SQLiteでキー管理）

search_by_image が失敗しても、ジョブ全体が即死せず、可能な範囲で続行する

19. Cursorへの実装指示（最短で作らせるためのプロンプト）

以下を Cursor にそのまま貼り付けてください（タスク分割済み）。

この仕様書のディレクトリ構成でPythonプロジェクトを生成してください。

app/main.py にエントリーポイントを作り、--once --dry-run --only-item を実装してください。

eBay認証（client credentials）を app/ebay/auth.py に実装し、トークンをキャッシュ（有効期限まで再利用）してください。

item_summary/search（sellers と buyingOptions フィルタ）を app/ebay/browse.py に実装してください。

item_summary/search_by_image（Base64画像）を実装してください。

SHA-256完全一致マッチャーを app/match/ に実装し、設定で URL一致も補助にできるようにしてください。

SQLiteのテーブルを app/store/db.py で作成し、重複検知キー（your_item_id × infringing_item_id）で二重登録を防いでください。

Google Sheets 追記を app/sheets/ に実装し、列スキーマは app/sheets/schema.py に定義してください。

メッセージ生成を app/msg/ に実装し、テンプレのプレースホルダを埋めてシートに出してください。

失敗時の分岐（OAuth失敗は即終了、それ以外は可能な範囲で継続）を実装してください。ログに run サマリを必ず出してください。