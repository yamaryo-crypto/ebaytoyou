"""Google Sheets API（サービスアカウント）で detections シートに追記。"""
from __future__ import annotations

import os
from typing import Any, List, Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

from app.sheets import schema

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _get_service():
    path = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_PATH", "./secrets/service_account.json")
    creds = service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)


def append_detections(
    rows: List[List[Any]],
    sheet_id: Optional[str] = None,
    worksheet_name: str = "detections",
) -> None:
    """指定シートの worksheet に rows を追記。"""
    sheet_id = sheet_id or os.getenv("GOOGLE_SHEETS_ID")
    if not sheet_id:
        raise ValueError("GOOGLE_SHEETS_ID must be set")
    service = _get_service()
    body = {"values": rows}
    service.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=f"'{worksheet_name}'!A:Z",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body=body,
    ).execute()


def ensure_header_row(
    sheet_id: Optional[str] = None,
    worksheet_name: str = "detections",
) -> None:
    """先頭行がヘッダでない場合のみ書き込む（簡易：既にデータがある場合はスキップ）。"""
    sheet_id = sheet_id or os.getenv("GOOGLE_SHEETS_ID")
    if not sheet_id:
        return
    service = _get_service()
    result = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=f"'{worksheet_name}'!A1:L1",
    ).execute()
    values = result.get("values", [])
    if not values:
        service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"'{worksheet_name}'!A1",
            valueInputOption="RAW",
            body={"values": [schema.COLUMNS]},
        ).execute()
