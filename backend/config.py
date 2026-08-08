import os
import secrets
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    GOOGLE_SERVICE_ACCOUNT_FILE: str = "credentials/google-service-account.json"
    GOOGLE_SHEET_ID: str = ""
    GOOGLE_WORKSHEET_NAME: str = "Form Responses 1"

    COLUMN_MAP_NAME: str = "Name"
    COLUMN_MAP_PHONE: str = "Mobile"
    COLUMN_MAP_EMAIL: str = "Email"
    COLUMN_MAP_CONSENT: str = "WhatsApp Consent"

    COUNTRY_CODE: str = "91"

    MIN_DELAY_SECONDS: int = 8
    MAX_DELAY_SECONDS: int = 20

    WHATSAPP_PROFILE_DIR: str = "data/whatsapp-profile"
    WHATSAPP_HEADLESS: bool = False

    OPT_OUT_KEYWORDS: str = "STOP,UNSUBSCRIBE,CANCEL,REMOVE"
    INBOX_POLL_INTERVAL_SECONDS: int = 90

    TEST_MODE: bool = False
    API_TOKEN: str = ""

    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'data' / 'q9x_dashboard.db'}"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def opt_out_keywords_list(self) -> list[str]:
        return [k.strip().upper() for k in self.OPT_OUT_KEYWORDS.split(",") if k.strip()]

settings = Settings()

def ensure_dirs():
    (BASE_DIR / "data").mkdir(exist_ok=True)
    (BASE_DIR / "credentials").mkdir(exist_ok=True)
    (BASE_DIR / "logs").mkdir(exist_ok=True)

def get_or_create_api_token() -> str:
    env_path = BASE_DIR / ".env"
    token = settings.API_TOKEN.strip()
    if not token:
        token = secrets.token_hex(24)
        settings.API_TOKEN = token
        # Write/Update token in .env if exists or create .env
        env_content = ""
        if env_path.exists():
            env_content = env_path.read_text(encoding="utf-8")
        if "API_TOKEN=" in env_content:
            lines = env_content.splitlines()
            new_lines = []
            for line in lines:
                if line.startswith("API_TOKEN="):
                    new_lines.append(f"API_TOKEN={token}")
                else:
                    new_lines.append(line)
            env_content = "\n".join(new_lines) + "\n"
        else:
            if env_content and not env_content.endswith("\n"):
                env_content += "\n"
            env_content += f"API_TOKEN={token}\n"
        env_path.write_text(env_content, encoding="utf-8")
    return token
