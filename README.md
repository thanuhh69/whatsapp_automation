# Q9X WhatsApp Communication Dashboard

A locally runnable, consent-enforced WhatsApp communication management dashboard built for **Q9X**. Automatically syncs registration forms from Google Sheets, normalizes phone numbers, handles campaign templating with dynamic variables (`{{name}}`, `{{email}}`), manages opt-outs, and executes visible Playwright browser automation with conservative pacing.

---

## 0. RISK ACKNOWLEDGEMENT & COMPLIANCE NOTE

> [!WARNING]
> **WhatsApp Browser Automation Risk Notice**:
> WhatsApp Web browser automation (even fully consent-based, low-volume, and well-paced) is **outside WhatsApp's official Business API terms**. Phone numbers can be rate-limited or temporarily restricted by WhatsApp regardless of conservative pacing.
> This is a known, accepted risk for this local internal organization tool.
>
> **Scaling Path**: If message volume exceeds a few hundred per week, migrate to the official **WhatsApp Business Platform (Cloud API)**.

---

## 1. PROJECT STRUCTURE

```
q9x-whatsapp-dashboard/
├── backend/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app & static file mounting
│   ├── config.py                # Environment & settings loader
│   ├── database.py              # SQLAlchemy engine & SQLite setup
│   ├── models.py                # Database models (Recipients, Campaigns, OptOuts, etc.)
│   ├── schemas.py               # Pydantic request/response schemas
│   ├── auth.py                  # Local API bearer token verification
│   ├── services/
│   │   ├── __init__.py
│   │   ├── google_sheets.py     # Google Sheets reader & deduplication engine
│   │   ├── whatsapp.py          # Playwright Chromium WhatsApp Web service
│   │   ├── whatsapp_inbox.py    # Auto opt-out keyword poller (STOP, UNSUBSCRIBE)
│   │   ├── campaign.py          # Campaign runner & pacing controller
│   │   ├── recipient.py         # Phone normalization & filtering rules
│   │   └── message_template.py  # Variable renderer ({{name}}, {{email}})
│   └── api/
│       ├── __init__.py
│       ├── dashboard.py         # /api/dashboard/stats
│       ├── recipients.py        # /api/recipients & /api/recipients/sync
│       ├── campaigns.py         # /api/campaigns (create, start, stop, view)
│       ├── whatsapp.py          # /api/whatsapp (connect, disconnect, status)
│       ├── templates.py         # /api/templates
│       ├── opt_outs.py          # /api/opt-outs
│       └── settings.py          # /api/settings
├── frontend/
│   ├── index.html               # SPA dashboard HTML structure
│   ├── css/
│   │   └── style.css            # Dark mode UI styling with glassmorphism
│   └── js/
│       ├── app.js               # SPA navigation & API fetch wrapper
│       ├── dashboard.js         # Stats widget controllers
│       ├── campaigns.js         # Campaign wizard & progress monitor
│       ├── recipients.js        # Recipient table & search filtering
│       ├── whatsapp.js          # QR session UI controller
│       ├── templates.js         # Template editor & live preview
│       └── opt_outs.js          # Opt-out directory UI
├── data/                        # Persistent SQLite database & WhatsApp session profile
├── credentials/                 # Google Service Account JSON key (gitignored)
├── logs/                        # Application log files (app.log)
├── tests/                       # Automated pytest suite
│   ├── test_phone_validation.py
│   ├── test_message_template.py
│   ├── test_database.py
│   ├── test_recipient_sync.py
│   └── test_opt_out.py
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
└── run.py                       # One-click application launcher
```

---

## 2. INSTALLATION COMMANDS

### macOS / Linux
```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Playwright Chromium browser
playwright install chromium
```

### Windows (PowerShell)
```powershell
# 1. Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Playwright Chromium browser
playwright install chromium
```

---

## 3. GOOGLE SHEETS SETUP INSTRUCTIONS

To sync registrants from Google Sheets:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project and enable the **Google Sheets API**.
3. Create a **Service Account** under *IAM & Admin -> Service Accounts*.
4. Generate a Service Account key in **JSON** format and download it.
5. Save the JSON file to `credentials/google-service-account.json`.
6. Open your target Google Sheet containing registration responses.
7. Click **Share** and share the sheet with your Service Account email address (Viewer access is sufficient).
8. Copy the Sheet ID from the URL (`https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit`) and update `.env` or the **Settings** view in the UI.

Expected Sheet Column Headers: `Name | Mobile | Email | WhatsApp Consent | Registration Date`

---

## 4. ENVIRONMENT VARIABLES (`.env`)

Create a `.env` file from `.env.example`:

```ini
GOOGLE_SERVICE_ACCOUNT_FILE=credentials/google-service-account.json
GOOGLE_SHEET_ID=YOUR_SHEET_ID
GOOGLE_WORKSHEET_NAME=Form Responses 1

COUNTRY_CODE=91

MIN_DELAY_SECONDS=8
MAX_DELAY_SECONDS=20

WHATSAPP_PROFILE_DIR=data/whatsapp-profile
WHATSAPP_HEADLESS=false

OPT_OUT_KEYWORDS=STOP,UNSUBSCRIBE,CANCEL,REMOVE
INBOX_POLL_INTERVAL_SECONDS=90

TEST_MODE=true
API_TOKEN=
```

*(Note: If `API_TOKEN` is blank, `run.py` automatically generates a secure 24-byte random hex token on first startup).*

---

## 5. STARTING THE APPLICATION

Run the launcher script:
```bash
python run.py
```

- **Dashboard URL**: `http://127.0.0.1:8000`
- **Security Token**: Printed in the console output upon launch. Enter this token into the "API Authorization Token" widget on the dashboard or header to allow mutating actions.

---

## 6. USER WORKFLOW GUIDE

### Connecting WhatsApp Web
1. Navigate to the **WhatsApp Connection** tab.
2. Click **Launch WhatsApp Web for QR Login**.
3. A visible Chromium window will pop up loading `https://web.whatsapp.com`.
4. Scan the QR code using WhatsApp on your phone.
5. Once logged in, the status indicator turns green (**CONNECTED**). The profile is saved locally in `data/whatsapp-profile/` for automatic login on subsequent app starts.

### Syncing Registrations
1. Navigate to **Recipients** or click **Sync Sheet** in the top header.
2. The app fetches rows from Google Sheets, normalizes phone numbers (e.g. `919876543210`), filters consent (`YES`/`TRUE`), deduplicates duplicates by keeping the latest registration date, excludes opted-out numbers, and updates SQLite.

### Running Test Mode vs. Real Campaigns
- **Test Mode** (Default): When `TEST_MODE=true` or campaign `is_test_mode=True`, message delivery is simulated with realistic timing delays without opening WhatsApp or sending messages. Use this mode to test templates and recipient selection safely.
- **Real Mode**: Set `TEST_MODE=false` in Settings/`.env` and uncheck "Run in Test Mode" during campaign creation to trigger real Playwright message delivery over WhatsApp Web.

### Automated Opt-Out Keyword Listening (§17)
While WhatsApp is connected, the **Inbox Poller** periodically checks open recent chats every 90 seconds. If an inbound message matches keywords (`STOP`, `UNSUBSCRIBE`, `CANCEL`, `REMOVE`), the sender's number is automatically added to the `opt_outs` table (`source=auto_keyword`) and blocked from all future sends.

---

## 7. AUTOMATED TESTING

Run the comprehensive unit test suite:
```bash
pytest -v
```

Tests cover:
- Indian phone number normalization & validation
- Variable template interpolation & missing variable handling
- Database creation & unique phone constraints
- Google Sheet sync deduplication & sync idempotency (running twice produces 0 duplicate records)
- Manual and auto-keyword opt-outs

---

## 8. LOGGING & TROUBLESHOOTING

- **Logs location**: `logs/app.log`
- **Session profile**: `data/whatsapp-profile/`
- **SQLite Database**: `data/q9x_dashboard.db`

### Common Issues & Fixes:
1. **Google Sheets Sync Error**: Ensure `credentials/google-service-account.json` exists and the sheet is shared with the service account email.
2. **WhatsApp Web Disconnect**: If WhatsApp Web logs out, click "Launch WhatsApp Web for QR Login" to re-scan the QR code.
3. **401/403 Unauthorized API Errors**: Copy the `Security Token` printed by `python run.py` and paste it into the "API Authorization Token" field on the dashboard.
