import re
from typing import Tuple, Optional, List
from sqlalchemy.orm import Session
from backend.config import settings
from backend.models import Recipient, OptOut

def normalize_phone(raw_phone: str, country_code: str = None) -> Tuple[Optional[str], bool]:
    """
    Normalizes a raw phone number based on country code rule.
    Returns (normalized_phone, is_valid).
    Follows Section 7 specifications for India (91) & configurable default.
    """
    if not raw_phone:
        return None, False

    cc = (country_code or settings.COUNTRY_CODE).strip()
    s = str(raw_phone).strip()

    # 1. Strip all non-digits
    cleaned = re.sub(r"\D", "", s)

    if not cleaned:
        return None, False

    if cc == "91":
        # 2 & 3. Handle 12-digit (91...), 11-digit (0...), or 10-digit numbers
        if len(cleaned) == 12 and cleaned.startswith("91"):
            cleaned = cleaned[2:]
        elif len(cleaned) == 11 and cleaned.startswith("0"):
            cleaned = cleaned[1:]

        # 4. Check 10 digits starting with 6-9
        if len(cleaned) == 10 and re.match(r"^[6-9]\d{9}$", cleaned):
            normalized = f"91{cleaned}"
            return normalized, True
        else:
            return None, False
    else:
        # Generalized rule for non-India country code
        if cleaned.startswith(cc):
            cleaned_local = cleaned[len(cc):]
        else:
            cleaned_local = cleaned

        if 7 <= len(cleaned_local) <= 12:
            return f"{cc}{cleaned_local}", True
        return None, False


def get_opted_out_phones(db: Session) -> set[str]:
    """Returns set of all normalized opted-out phone numbers."""
    opt_outs = db.query(OptOut.phone).all()
    return {row.phone for row in opt_outs}


def get_eligible_recipients(db: Session) -> List[Recipient]:
    """
    Returns list of recipients eligible for sends:
    - consent == True
    - phone not in opt_outs table
    """
    opt_out_set = get_opted_out_phones(db)
    recipients = db.query(Recipient).filter(Recipient.consent == True).all()
    return [r for r in recipients if r.phone not in opt_out_set]
