import asyncio
import random
import logging
from datetime import datetime
from typing import Dict, Optional, List
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import SessionLocal
from backend.models import Campaign, CampaignMessage, Recipient, OptOut
from backend.services.message_template import render_template
from backend.services.whatsapp import whatsapp_service

logger = logging.getLogger("q9x_app")

active_campaign_tasks: Dict[int, asyncio.Task] = {}
campaign_stop_flags: Dict[int, bool] = {}

def create_campaign(db: Session, name: str, message_template: str, recipient_ids: Optional[List[int]] = None, is_test_mode: bool = False) -> Campaign:
    """
    Creates a campaign and populates campaign_messages table.
    """
    opt_out_set = {r.phone for r in db.query(OptOut.phone).all()}

    query = db.query(Recipient).filter(Recipient.consent == True)
    if recipient_ids:
        query = query.filter(Recipient.id.in_(recipient_ids))
    recipients = query.all()

    campaign = Campaign(
        name=name,
        message_template=message_template,
        status="DRAFT",
        created_at=datetime.utcnow(),
        total_recipients=len(recipients),
        is_test_mode=is_test_mode
    )
    db.add(campaign)
    db.flush()

    for r in recipients:
        if r.phone in opt_out_set:
            status = "OPTED_OUT"
            rendered = "[Skipped - Recipient Opted Out]"
            error_msg = "Recipient is on the opt-out list"
            campaign.skipped_count += 1
        else:
            context = {"name": r.name, "email": r.email or ""}
            rendered, ok, err = render_template(message_template, context)
            if not ok:
                status = "SKIPPED"
                error_msg = err
                campaign.skipped_count += 1
            else:
                status = "PENDING"
                error_msg = None

        cm = CampaignMessage(
            campaign_id=campaign.id,
            recipient_id=r.id,
            rendered_message=rendered,
            status=status,
            error=error_msg
        )
        db.add(cm)

    db.commit()
    db.refresh(campaign)
    return campaign


async def start_campaign_task(campaign_id: int):
    """
    Background worker task for processing campaign messages.
    """
    db = SessionLocal()
    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            return

        campaign.status = "SENDING"
        campaign.started_at = datetime.utcnow()
        db.commit()

        campaign_stop_flags[campaign_id] = False
        is_test = campaign.is_test_mode and settings.TEST_MODE

        logger.info(f"Started campaign '{campaign.name}' (ID: {campaign_id}, Real WhatsApp Mode: {not is_test})")

        messages = db.query(CampaignMessage).filter(
            CampaignMessage.campaign_id == campaign_id,
            CampaignMessage.status == "PENDING"
        ).all()

        for cm in messages:
            if campaign_stop_flags.get(campaign_id, False):
                logger.info(f"Campaign {campaign_id} received stop signal. Stopping further sends.")
                break

            cm.status = "SENDING"
            db.commit()

            recipient = db.query(Recipient).filter(Recipient.id == cm.recipient_id).first()
            if not recipient:
                cm.status = "FAILED"
                cm.error = "Recipient record missing"
                campaign.failed_count += 1
                db.commit()
                continue

            opt_exists = db.query(OptOut).filter(OptOut.phone == recipient.phone).first()
            if opt_exists:
                cm.status = "OPTED_OUT"
                cm.error = "Recipient opted out during campaign"
                campaign.skipped_count += 1
                db.commit()
                continue

            if is_test:
                delay = random.uniform(0.5, 1.5)
                await asyncio.sleep(delay)
                cm.status = "SENT"
                cm.sent_at = datetime.utcnow()
                campaign.sent_count += 1
                logger.info(f"[TEST MODE] Simulated send to {recipient.name} ({recipient.phone})")
            else:
                success, err = await whatsapp_service.send_message(recipient.phone, cm.rendered_message)
                if success:
                    cm.status = "SENT"
                    cm.sent_at = datetime.utcnow()
                    campaign.sent_count += 1
                else:
                    cm.status = "FAILED"
                    cm.error = err or "WhatsApp Web delivery failed"
                    campaign.failed_count += 1

                delay = random.uniform(settings.MIN_DELAY_SECONDS, settings.MAX_DELAY_SECONDS)
                await asyncio.sleep(delay)

            db.commit()

        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if campaign_stop_flags.get(campaign_id, False):
            campaign.status = "STOPPED"
        else:
            campaign.status = "COMPLETED"
            campaign.completed_at = datetime.utcnow()

        db.commit()

    except Exception as e:
        logger.error(f"Error executing campaign {campaign_id}: {e}")
        if campaign:
            campaign.status = "FAILED"
            db.commit()
    finally:
        db.close()
        campaign_stop_flags.pop(campaign_id, None)
        active_campaign_tasks.pop(campaign_id, None)


def trigger_start_campaign(campaign_id: int) -> bool:
    if campaign_id in active_campaign_tasks and not active_campaign_tasks[campaign_id].done():
        return False
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.get_event_loop()
    task = loop.create_task(start_campaign_task(campaign_id))
    active_campaign_tasks[campaign_id] = task
    return True


def trigger_stop_campaign(campaign_id: int) -> bool:
    if campaign_id in active_campaign_tasks:
        campaign_stop_flags[campaign_id] = True
        return True
    return False


def delete_campaign(db: Session, campaign_id: int) -> bool:
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        return False
    if campaign_id in active_campaign_tasks:
        trigger_stop_campaign(campaign_id)
    db.query(CampaignMessage).filter(CampaignMessage.campaign_id == campaign_id).delete()
    db.query(Campaign).filter(Campaign.id == campaign_id).delete()
    db.commit()
    return True


def bulk_delete_campaigns(db: Session, campaign_ids: List[int]) -> int:
    deleted = 0
    for cid in campaign_ids:
        if delete_campaign(db, cid):
            deleted += 1
    return deleted


def retry_failed_messages(db: Session, campaign_id: int) -> int:
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        return 0

    failed_msgs = db.query(CampaignMessage).filter(
        CampaignMessage.campaign_id == campaign_id,
        CampaignMessage.status == "FAILED"
    ).all()

    opt_out_set = {r.phone for r in db.query(OptOut.phone).all()}
    count = 0
    for cm in failed_msgs:
        rec = db.query(Recipient).filter(Recipient.id == cm.recipient_id).first()
        if not rec or rec.phone in opt_out_set or rec.status == "DEACTIVATED":
            cm.status = "SKIPPED"
            cm.error = "Recipient unavailable, opted out, or deactivated"
        else:
            cm.status = "PENDING"
            cm.error = None
            count += 1

    campaign.failed_count = max(0, campaign.failed_count - count)
    campaign.status = "DRAFT"
    db.commit()
    return count
