import os
import re
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.schemas import SettingsOut, SettingsUpdate, AdminResetRequest
from backend.auth import verify_bearer_token
from backend.config import settings, BASE_DIR
from backend.database import get_db
from backend.models import Recipient, Campaign, CampaignMessage, OptOut, InboundMessage
from backend.services.google_sheets import fetch_sheet_headers, get_gspread_worksheet

router = APIRouter(prefix="/api/settings", tags=["Settings"])

def extract_sheet_id(val: str) -> str:
    if not val:
        return ""
    s = val.strip()
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", s)
    if match:
        return match.group(1)
    return s

def save_env_setting(key: str, value: str):
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    content = env_path.read_text(encoding="utf-8")
    pattern = rf"^{key}=.*$"
    replacement = f"{key}={value}"
    if re.search(pattern, content, flags=re.MULTILINE):
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    else:
        new_content = content.rstrip() + f"\n{key}={value}\n"
    env_path.write_text(new_content, encoding="utf-8")


@router.get("", response_model=SettingsOut)
def get_settings():
    return SettingsOut(
        GOOGLE_SHEET_ID=settings.GOOGLE_SHEET_ID,
        GOOGLE_WORKSHEET_NAME=settings.GOOGLE_WORKSHEET_NAME,
        COLUMN_MAP_NAME=settings.COLUMN_MAP_NAME,
        COLUMN_MAP_PHONE=settings.COLUMN_MAP_PHONE,
        COLUMN_MAP_EMAIL=settings.COLUMN_MAP_EMAIL,
        COLUMN_MAP_CONSENT=settings.COLUMN_MAP_CONSENT,
        COUNTRY_CODE=settings.COUNTRY_CODE,
        MIN_DELAY_SECONDS=settings.MIN_DELAY_SECONDS,
        MAX_DELAY_SECONDS=settings.MAX_DELAY_SECONDS,
        WHATSAPP_HEADLESS=settings.WHATSAPP_HEADLESS,
        OPT_OUT_KEYWORDS=settings.OPT_OUT_KEYWORDS,
        INBOX_POLL_INTERVAL_SECONDS=settings.INBOX_POLL_INTERVAL_SECONDS,
        TEST_MODE=settings.TEST_MODE
    )


@router.put("", response_model=SettingsOut, dependencies=[Depends(verify_bearer_token)])
def update_settings(payload: SettingsUpdate):
    if payload.GOOGLE_SHEET_ID is not None:
        extracted = extract_sheet_id(payload.GOOGLE_SHEET_ID)
        settings.GOOGLE_SHEET_ID = extracted
        save_env_setting("GOOGLE_SHEET_ID", extracted)
    if payload.GOOGLE_WORKSHEET_NAME is not None:
        settings.GOOGLE_WORKSHEET_NAME = payload.GOOGLE_WORKSHEET_NAME.strip()
        save_env_setting("GOOGLE_WORKSHEET_NAME", settings.GOOGLE_WORKSHEET_NAME)
    if payload.COLUMN_MAP_NAME is not None:
        settings.COLUMN_MAP_NAME = payload.COLUMN_MAP_NAME.strip()
        save_env_setting("COLUMN_MAP_NAME", settings.COLUMN_MAP_NAME)
    if payload.COLUMN_MAP_PHONE is not None:
        settings.COLUMN_MAP_PHONE = payload.COLUMN_MAP_PHONE.strip()
        save_env_setting("COLUMN_MAP_PHONE", settings.COLUMN_MAP_PHONE)
    if payload.COLUMN_MAP_EMAIL is not None:
        settings.COLUMN_MAP_EMAIL = payload.COLUMN_MAP_EMAIL.strip()
        save_env_setting("COLUMN_MAP_EMAIL", settings.COLUMN_MAP_EMAIL)
    if payload.COLUMN_MAP_CONSENT is not None:
        settings.COLUMN_MAP_CONSENT = payload.COLUMN_MAP_CONSENT.strip()
        save_env_setting("COLUMN_MAP_CONSENT", settings.COLUMN_MAP_CONSENT)
    if payload.COUNTRY_CODE is not None:
        settings.COUNTRY_CODE = payload.COUNTRY_CODE.strip()
        save_env_setting("COUNTRY_CODE", settings.COUNTRY_CODE)
    if payload.MIN_DELAY_SECONDS is not None:
        settings.MIN_DELAY_SECONDS = max(1, payload.MIN_DELAY_SECONDS)
        save_env_setting("MIN_DELAY_SECONDS", str(settings.MIN_DELAY_SECONDS))
    if payload.MAX_DELAY_SECONDS is not None:
        settings.MAX_DELAY_SECONDS = max(settings.MIN_DELAY_SECONDS, payload.MAX_DELAY_SECONDS)
        save_env_setting("MAX_DELAY_SECONDS", str(settings.MAX_DELAY_SECONDS))
    if payload.WHATSAPP_HEADLESS is not None:
        settings.WHATSAPP_HEADLESS = payload.WHATSAPP_HEADLESS
        save_env_setting("WHATSAPP_HEADLESS", str(settings.WHATSAPP_HEADLESS).lower())
    if payload.OPT_OUT_KEYWORDS is not None:
        settings.OPT_OUT_KEYWORDS = payload.OPT_OUT_KEYWORDS.strip()
        save_env_setting("OPT_OUT_KEYWORDS", settings.OPT_OUT_KEYWORDS)
    if payload.INBOX_POLL_INTERVAL_SECONDS is not None:
        settings.INBOX_POLL_INTERVAL_SECONDS = max(10, payload.INBOX_POLL_INTERVAL_SECONDS)
        save_env_setting("INBOX_POLL_INTERVAL_SECONDS", str(settings.INBOX_POLL_INTERVAL_SECONDS))
    if payload.TEST_MODE is not None:
        settings.TEST_MODE = payload.TEST_MODE
        save_env_setting("TEST_MODE", str(settings.TEST_MODE).lower())

    return get_settings()


@router.get("/sheet-headers")
def get_sheet_headers():
    try:
        headers = fetch_sheet_headers()
        return {"headers": headers}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch sheet headers: {str(e)}")


@router.post("/test-connection")
def test_sheet_connection():
    try:
        ws = get_gspread_worksheet()
        title = ws.spreadsheet.title
        rows_count = len(ws.get_all_records())
        return {
            "status": "success",
            "message": f"Successfully connected to '{title}' ({rows_count} records found)."
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Google Sheet connection test failed: {str(e)}")


@router.delete("/credentials", dependencies=[Depends(verify_bearer_token)])
def delete_credentials():
    sa_file = BASE_DIR / settings.GOOGLE_SERVICE_ACCOUNT_FILE
    if sa_file.exists():
        sa_file.unlink()
    settings.GOOGLE_SHEET_ID = ""
    save_env_setting("GOOGLE_SHEET_ID", "")
    return {"message": "Google Service Account credentials and Sheet ID cleared successfully"}


@router.post("/admin-reset", dependencies=[Depends(verify_bearer_token)])
def admin_reset_database(payload: AdminResetRequest, db: Session = Depends(get_db)):
    rt = payload.reset_type.lower()
    if rt == "recipients":
        count = db.query(Recipient).delete()
        db.commit()
        return {"message": f"Cleared {count} local recipients. Google Sheet remains untouched."}
    elif rt == "campaigns":
        db.query(CampaignMessage).delete()
        count = db.query(Campaign).delete()
        db.commit()
        return {"message": f"Cleared {count} campaigns and all delivery message logs."}
    elif rt == "messages":
        count = db.query(CampaignMessage).delete()
        db.commit()
        return {"message": f"Cleared {count} message delivery logs."}
    elif rt == "full_database":
        db.query(CampaignMessage).delete()
        db.query(Campaign).delete()
        db.query(Recipient).delete()
        db.query(OptOut).delete()
        db.query(InboundMessage).delete()
        db.commit()
        return {"message": "Reset entire local database cleanly. All tables cleared."}
    else:
        raise HTTPException(status_code=400, detail=f"Invalid reset_type: '{payload.reset_type}'")
