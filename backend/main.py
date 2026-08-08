import os
import asyncio
import logging
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from backend.config import settings, BASE_DIR, ensure_dirs, get_or_create_api_token
from backend.database import init_db

# Configure application logging
ensure_dirs()
log_file = BASE_DIR / "logs" / "app.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("q9x_app")

app = FastAPI(
    title="Q9X WhatsApp Communication Dashboard",
    version="1.0.0",
    description="Locally runnable WhatsApp communication dashboard for Q9X"
)

# CORS middleware for local frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
from backend.api import dashboard, recipients, campaigns, whatsapp, templates, opt_outs, settings as settings_api

app.include_router(dashboard.router)
app.include_router(recipients.router)
app.include_router(campaigns.router)
app.include_router(whatsapp.router)
app.include_router(templates.router)
app.include_router(opt_outs.router)
app.include_router(settings_api.router)

# Mount frontend directory
frontend_dir = BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

@app.on_event("startup")
async def on_startup():
    logger.info("Initializing Q9X Dashboard database...")
    init_db()
    token = get_or_create_api_token()
    logger.info(f"Q9X Dashboard ready. API Bearer Token: {token}")

    storage_file = BASE_DIR / settings.WHATSAPP_PROFILE_DIR / "storage.json"
    if storage_file.exists() and storage_file.stat().st_size > 50:
        logger.info("Saved WhatsApp Web session found. Auto-reconnecting background session...")
        from backend.services.whatsapp import whatsapp_service
        asyncio.create_task(whatsapp_service.connect())

@app.get("/")
def serve_index():
    index_file = BASE_DIR / "frontend" / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse({"message": "Q9X WhatsApp Dashboard API server is running."})
