import asyncio
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import SessionLocal
from backend.models import OptOut, InboundMessage
from backend.services.recipient import normalize_phone

logger = logging.getLogger("q9x_app")

class InboxPoller:
    def __init__(self):
        self.is_running = False
        self._task: Optional[asyncio.Task] = None

    def start(self, whatsapp_service):
        if self.is_running:
            return
        self.is_running = True
        self._task = asyncio.create_task(self._poll_loop(whatsapp_service))
        logger.info("WhatsApp Inbox Poller background task started.")

    def stop(self):
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("WhatsApp Inbox Poller background task stopped.")

    async def _poll_loop(self, whatsapp_service):
        while self.is_running:
            try:
                await asyncio.sleep(settings.INBOX_POLL_INTERVAL_SECONDS)
                if not whatsapp_service.is_connected():
                    continue

                inbound_records = await whatsapp_service.fetch_inbound_messages()
                if inbound_records:
                    db = SessionLocal()
                    try:
                        for record in inbound_records:
                            self.process_inbound_message(db, record.get("phone", ""), record.get("body", ""))
                    finally:
                        db.close()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in inbox poller loop: {e}")

    @staticmethod
    def process_inbound_message(db: Session, phone_raw: str, body: str) -> bool:
        """
        Processes an inbound message, checks for opt-out keywords.
        Returns True if opt-out matched and created.
        """
        normalized_phone, is_valid = normalize_phone(phone_raw)
        if not is_valid or not normalized_phone:
            normalized_phone = phone_raw.strip()

        clean_body = body.strip()
        matched_kw = None

        keywords = settings.opt_out_keywords_list
        words = [w.strip().upper() for w in clean_body.split()]
        for kw in keywords:
            if kw in words or clean_body.upper() == kw:
                matched_kw = kw
                break

        inbound = InboundMessage(
            phone=normalized_phone,
            body=clean_body,
            received_at=datetime.utcnow(),
            matched_keyword=matched_kw
        )
        db.add(inbound)

        opt_created = False
        if matched_kw:
            existing = db.query(OptOut).filter(OptOut.phone == normalized_phone).first()
            if not existing:
                opt_out = OptOut(
                    phone=normalized_phone,
                    reason=f"Automatic keyword match: '{matched_kw}'",
                    source="auto_keyword"
                )
                db.add(opt_out)
                opt_created = True
                logger.info(f"Auto opt-out recorded for phone '{normalized_phone}' via keyword '{matched_kw}'")

        db.commit()
        return opt_created

inbox_poller = InboxPoller()
