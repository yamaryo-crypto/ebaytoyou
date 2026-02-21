#!/usr/bin/env bash
# プロジェクトルートで実行すること
set -e
cd "$(dirname "$0")/.."
. .venv/bin/activate
python -m app.main --once
