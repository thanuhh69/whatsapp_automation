from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from backend.database import get_db
from backend.models import Campaign, CampaignMessage, Recipient
from backend.schemas import CampaignOut, CampaignCreate, CampaignMessageOut
from backend.auth import verify_bearer_token
from backend.services.campaign import create_campaign, trigger_start_campaign, trigger_stop_campaign

router = APIRouter(prefix="/api/campaigns", tags=["Campaigns"])

@router.get("", response_model=List[CampaignOut])
def list_campaigns(db: Session = Depends(get_db)):
    return db.query(Campaign).order_by(Campaign.id.desc()).all()


@router.post("", response_model=CampaignOut, dependencies=[Depends(verify_bearer_token)])
def create_new_campaign(payload: CampaignCreate, db: Session = Depends(get_db)):
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="Campaign name cannot be empty")
    if not payload.message_template.strip():
        raise HTTPException(status_code=400, detail="Message template cannot be empty")

    campaign = create_campaign(
        db,
        name=payload.name,
        message_template=payload.message_template,
        recipient_ids=payload.recipient_ids,
        is_test_mode=payload.is_test_mode
    )
    return campaign


@router.get("/{id}", response_model=CampaignOut)
def get_campaign(id: int, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.post("/{id}/start", dependencies=[Depends(verify_bearer_token)])
async def start_campaign_endpoint(id: int, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status == "SENDING":
        return {"message": "Campaign is already running"}
    if campaign.status in ["COMPLETED"]:
        raise HTTPException(status_code=400, detail="Campaign has already completed")

    started = trigger_start_campaign(id)
    if started:
        return {"status": "started", "message": f"Campaign '{campaign.name}' started"}
    else:
        return {"status": "busy", "message": "Campaign task is already active"}


@router.post("/{id}/stop", dependencies=[Depends(verify_bearer_token)])
async def stop_campaign_endpoint(id: int, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    stopped = trigger_stop_campaign(id)
    if stopped:
        return {"status": "stopping", "message": "Stop signal sent to campaign runner. In-flight message will finish."}
    else:
        return {"status": "not_running", "message": "Campaign is not currently running"}


@router.get("/{id}/messages", response_model=dict)
def get_campaign_messages(
    id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(CampaignMessage).filter(CampaignMessage.campaign_id == id)
    if status:
        query = query.filter(CampaignMessage.status == status)

    total = query.count()
    start = (page - 1) * page_size
    items = query.order_by(CampaignMessage.id.asc()).offset(start).limit(page_size).all()

    # Populate recipient fields
    results = []
    for m in items:
        out = CampaignMessageOut.model_validate(m)
        rec = db.query(Recipient).filter(Recipient.id == m.recipient_id).first()
        if rec:
            out.recipient_name = rec.name
            out.recipient_phone = rec.phone
        results.append(out)

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": results
    }


@router.delete("/{id}", dependencies=[Depends(verify_bearer_token)])
def delete_campaign_endpoint(id: int, db: Session = Depends(get_db)):
    from backend.services.campaign import delete_campaign
    success = delete_campaign(db, id)
    if not success:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {"message": f"Campaign #{id} deleted successfully."}


@router.post("/bulk-delete", dependencies=[Depends(verify_bearer_token)])
def bulk_delete_campaigns_endpoint(payload: dict, db: Session = Depends(get_db)):
    ids = payload.get("campaign_ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="No campaign_ids provided")
    from backend.services.campaign import bulk_delete_campaigns
    count = bulk_delete_campaigns(db, ids)
    return {"message": f"Successfully deleted {count} campaigns."}


@router.post("/{id}/retry-failed", dependencies=[Depends(verify_bearer_token)])
def retry_failed_endpoint(id: int, db: Session = Depends(get_db)):
    from backend.services.campaign import retry_failed_messages
    count = retry_failed_messages(db, id)
    return {"message": f"Reset {count} failed messages back to PENDING for retry."}
