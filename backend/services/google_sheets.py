import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from backend.config import settings, BASE_DIR
from backend.models import Recipient, OptOut
from backend.services.recipient import normalize_phone

logger = logging.getLogger("q9x_app")

def parse_date(date_str: str) -> Optional[datetime]:
    if not date_str or not str(date_str).strip():
        return None
    s = str(date_str).strip()
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y",
        "%Y-%m-%dT%H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def get_gspread_worksheet():
    sa_file = BASE_DIR / settings.GOOGLE_SERVICE_ACCOUNT_FILE
    if not sa_file.exists():
        raise FileNotFoundError(
            f"Google Service Account JSON file not found at '{sa_file}'. "
            "Please configure credentials in settings."
        )
    if not settings.GOOGLE_SHEET_ID.strip():
        raise ValueError("GOOGLE_SHEET_ID is not configured in environment settings.")

    import gspread
    from google.oauth2.service_account import Credentials

    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(str(sa_file), scopes=scopes)
    client = gspread.authorize(creds)

    spreadsheet = client.open_by_key(settings.GOOGLE_SHEET_ID.strip())
    try:
        worksheet = spreadsheet.worksheet(settings.GOOGLE_WORKSHEET_NAME.strip())
    except Exception:
        worksheet = spreadsheet.sheet1
    return worksheet


def fetch_sheet_headers() -> List[str]:
    """
    Fetches the raw header list from row 1 of the configured Google Sheet.
    """
    worksheet = get_gspread_worksheet()
    row_1 = worksheet.row_values(1)
    return [str(col).strip() for col in row_1 if str(col).strip()]


def sync_google_sheets(
    db: Session,
    rows_override: Optional[List[Dict[str, Any]]] = None,
    replace_all: bool = False
) -> Dict[str, Any]:
    """
    Syncs registrants from Google Sheets (or rows_override for testing).
    Uses configured column mappings:
      Name -> settings.COLUMN_MAP_NAME
      Phone -> settings.COLUMN_MAP_PHONE
      Email -> settings.COLUMN_MAP_EMAIL
      Consent -> settings.COLUMN_MAP_CONSENT
    Deduplicates by normalized phone number.
    Returns detailed sync report stats.
    """
    added = 0
    updated = 0
    deactivated = 0
    ignored = 0
    invalid = 0
    duplicates = 0

    rows: List[Dict[str, Any]] = []

    if rows_override is not None:
        rows = rows_override
    else:
        worksheet = get_gspread_worksheet()
        rows = worksheet.get_all_records()

    phone_map: Dict[str, Dict[str, Any]] = {}
    opt_out_set = {r.phone for r in db.query(OptOut.phone).all()}

    col_name = (settings.COLUMN_MAP_NAME or "Name").strip().lower()
    col_phone = (settings.COLUMN_MAP_PHONE or "Mobile").strip().lower()
    col_email = (settings.COLUMN_MAP_EMAIL or "Email").strip().lower()
    col_consent = (settings.COLUMN_MAP_CONSENT or "WhatsApp Consent").strip().lower()

    for row_idx, raw_row in enumerate(rows):
        row = {str(k).strip().lower(): str(v).strip() for k, v in raw_row.items()}

        # 1. Extract values using mapped columns with intelligent fallbacks
        name = row.get(col_name) or row.get("name") or row.get("full name") or row.get("student name") or "Registrant"
        mobile_raw = row.get(col_phone) or row.get("mobile") or row.get("phone") or row.get("contact") or row.get("whatsapp number") or row.get("mobile number") or ""
        email = row.get(col_email) or row.get("email") or row.get("mail id") or row.get("email address") or None
        consent_raw = (row.get(col_consent) or row.get("whatsapp consent") or row.get("consent") or "").upper()
        reg_date_str = row.get("registration date") or row.get("timestamp") or row.get("date") or ""

        # 2. Validate and normalize phone number
        normalized_phone, is_valid = normalize_phone(mobile_raw)
        if not is_valid or not normalized_phone:
            invalid += 1
            logger.info(f"Sync: Invalid phone '{mobile_raw}' for recipient '{name}'")
            continue

        # 3. Consent check: if explicitly set to NO/FALSE, mark no consent
        if consent_raw in ["NO", "FALSE", "0", "N"]:
            ignored += 1
            logger.info(f"Sync: Ignored row (no consent) for '{name}' ({normalized_phone})")
            continue

        # 4. Opt-out check
        if normalized_phone in opt_out_set:
            ignored += 1
            logger.info(f"Sync: Ignored row (opted out) for '{name}' ({normalized_phone})")
            continue

        reg_dt = parse_date(reg_date_str) or datetime.utcnow()

        candidate = {
            "name": name,
            "phone": normalized_phone,
            "phone_raw": mobile_raw,
            "email": email,
            "consent": True,
            "registration_date": reg_dt,
            "row_idx": row_idx
        }

        if normalized_phone in phone_map:
            duplicates += 1
            existing = phone_map[normalized_phone]
            if candidate["registration_date"] >= existing["registration_date"]:
                phone_map[normalized_phone] = candidate
        else:
            phone_map[normalized_phone] = candidate

    synced_phones = set(phone_map.keys())

    # Handle replace_all option if specified
    if replace_all:
        all_existing = db.query(Recipient).all()
        for rec in all_existing:
            if rec.phone not in synced_phones and rec.status != "DEACTIVATED":
                rec.status = "DEACTIVATED"
                rec.updated_at = datetime.utcnow()
                deactivated += 1

    now = datetime.utcnow()
    for normalized_phone, data in phone_map.items():
        existing_rec = db.query(Recipient).filter(Recipient.phone == normalized_phone).first()
        if existing_rec:
            changed = False
            if existing_rec.name != data["name"]:
                existing_rec.name = data["name"]
                changed = True
            if existing_rec.email != data["email"]:
                existing_rec.email = data["email"]
                changed = True
            if existing_rec.phone_raw != data["phone_raw"]:
                existing_rec.phone_raw = data["phone_raw"]
                changed = True
            if existing_rec.status != "ACTIVE":
                existing_rec.status = "ACTIVE"
                changed = True

            existing_rec.last_synced_at = now
            if changed:
                existing_rec.updated_at = now
                updated += 1
        else:
            new_rec = Recipient(
                name=data["name"],
                phone=data["phone"],
                phone_raw=data["phone_raw"],
                email=data["email"],
                consent=True,
                status="ACTIVE",
                registration_date=data["registration_date"],
                last_synced_at=now
            )
            db.add(new_rec)
            added += 1

    db.commit()

    return {
        "added": added,
        "updated": updated,
        "deactivated": deactivated,
        "ignored": ignored,
        "invalid": invalid,
        "duplicates": duplicates,
        "last_synced": now.strftime("%Y-%m-%d %H:%M:%S")
    }
