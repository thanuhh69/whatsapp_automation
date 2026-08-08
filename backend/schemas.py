from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class RecipientBase(BaseModel):
    name: str
    phone_raw: str
    email: Optional[str] = None
    consent: bool = True
    registration_date: Optional[datetime] = None

class RecipientCreate(RecipientBase):
    pass

class RecipientOut(BaseModel):
    id: int
    name: str
    phone: str
    phone_raw: str
    email: Optional[str] = None
    consent: bool
    status: str = "ACTIVE"
    registration_date: Optional[datetime] = None
    last_synced_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    is_opted_out: bool = False

    class Config:
        from_attributes = True

class SyncReportOut(BaseModel):
    added: int
    updated: int
    deactivated: int = 0
    ignored: int
    invalid: int
    duplicates: int = 0
    last_synced: Optional[str] = None

class AdminResetRequest(BaseModel):
    reset_type: str # recipients | campaigns | messages | full_database

class CampaignCreate(BaseModel):
    name: str
    message_template: str
    recipient_ids: Optional[List[int]] = None
    is_test_mode: bool = True

class CampaignMessageOut(BaseModel):
    id: int
    campaign_id: int
    recipient_id: int
    recipient_name: Optional[str] = None
    recipient_phone: Optional[str] = None
    rendered_message: str
    status: str
    error: Optional[str] = None
    sent_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class CampaignOut(BaseModel):
    id: int
    name: str
    message_template: str
    status: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_recipients: int
    sent_count: int
    failed_count: int
    skipped_count: int
    is_test_mode: bool

    class Config:
        from_attributes = True

class OptOutCreate(BaseModel):
    phone: str
    reason: Optional[str] = "Manual admin opt-out"
    source: str = "manual"

class OptOutOut(BaseModel):
    id: int
    phone: str
    reason: Optional[str] = None
    source: str
    created_at: datetime

    class Config:
        from_attributes = True

class TemplateCreate(BaseModel):
    name: str
    content: str

class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None

class TemplateOut(BaseModel):
    id: str
    name: str
    content: str

class DashboardStatsOut(BaseModel):
    total_registrants: int
    eligible_recipients: int
    total_campaigns: int
    opt_out_count: int
    whatsapp_status: str
    test_mode_enabled: bool

class WhatsAppStatusOut(BaseModel):
    status: str # connected | disconnected | connecting | unknown
    qr_code_needed: bool = False

class SettingsOut(BaseModel):
    GOOGLE_SHEET_ID: str
    GOOGLE_WORKSHEET_NAME: str
    COLUMN_MAP_NAME: str = "Name"
    COLUMN_MAP_PHONE: str = "Mobile"
    COLUMN_MAP_EMAIL: str = "Email"
    COLUMN_MAP_CONSENT: str = "WhatsApp Consent"
    COUNTRY_CODE: str
    MIN_DELAY_SECONDS: int
    MAX_DELAY_SECONDS: int
    WHATSAPP_HEADLESS: bool
    OPT_OUT_KEYWORDS: str
    INBOX_POLL_INTERVAL_SECONDS: int
    TEST_MODE: bool

class SettingsUpdate(BaseModel):
    GOOGLE_SHEET_ID: Optional[str] = None
    GOOGLE_WORKSHEET_NAME: Optional[str] = None
    COLUMN_MAP_NAME: Optional[str] = None
    COLUMN_MAP_PHONE: Optional[str] = None
    COLUMN_MAP_EMAIL: Optional[str] = None
    COLUMN_MAP_CONSENT: Optional[str] = None
    COUNTRY_CODE: Optional[str] = None
    MIN_DELAY_SECONDS: Optional[int] = None
    MAX_DELAY_SECONDS: Optional[int] = None
    WHATSAPP_HEADLESS: Optional[bool] = None
    OPT_OUT_KEYWORDS: Optional[str] = None
    INBOX_POLL_INTERVAL_SECONDS: Optional[int] = None
    TEST_MODE: Optional[bool] = None
