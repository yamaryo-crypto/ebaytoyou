"""
CLI エントリーポイント。--once, --dry-run, --only-item を処理。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# プロジェクトルートをパスに追加
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="eBay image theft monitor")
    parser.add_argument("--once", action="store_true", help="Run job once")
    parser.add_argument("--dry-run", action="store_true", help="No API/DB/Sheets, log steps only")
    parser.add_argument("--only-item", type=str, metavar="ITEM_ID", help="Process only this item (your listing)")
    parser.add_argument(
        "--suspect-items",
        type=str,
        metavar="IDS",
        help="Comma-separated suspect item IDs to compare (use with --only-item)",
    )
    args = parser.parse_args()

    if not args.once:
        parser.print_help()
        sys.exit(0)

    from app.job import run_once

    suspect_ids = None
    if args.suspect_items:
        suspect_ids = [x.strip() for x in args.suspect_items.split(",") if x.strip()]
    run_once(
        dry_run=args.dry_run,
        only_item=args.only_item,
        suspect_item_ids=suspect_ids,
    )


if __name__ == "__main__":
    main()
