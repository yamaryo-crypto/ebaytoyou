#!/usr/bin/env bash
# Web UI を起動するスクリプト
set -e
cd "$(dirname "$0")/.."
. .venv/bin/activate
streamlit run app/web.py
