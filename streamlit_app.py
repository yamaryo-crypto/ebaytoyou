"""
Streamlit Community Cloud 用エントリーポイント。
app/web.py の内容をそのまま使用。
"""
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# app/web.py をインポート（実行される）
import app.web
