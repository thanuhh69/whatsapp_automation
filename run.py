import os
import sys
import uvicorn
from pathlib import Path

# Add project root directory to python path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from backend.config import settings, ensure_dirs, get_or_create_api_token
from backend.database import init_db

def main():
    print("=" * 65)
    print("      Q9X WhatsApp Communication Dashboard (v1.0.0)")
    print("=" * 65)

    ensure_dirs()
    init_db()
    token = get_or_create_api_token()

    print(f"\n [✓] Security Token: {token}")
    print(f" [✓] Server Binding: http://127.0.0.1:8000")
    print(f" [✓] Mode: {'TEST MODE (Simulated Sends)' if settings.TEST_MODE else 'PRODUCTION (Real WhatsApp Sends)'}")
    print("\n Launching server... Press Ctrl+C to stop.\n")

    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False
    )

if __name__ == "__main__":
    main()
