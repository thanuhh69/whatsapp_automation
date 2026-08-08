from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from backend.database import get_db
from backend.models import Recipient, OptOut
from backend.schemas import RecipientOut, SyncReportOut
from backend.auth import verify_bearer_token
from backend.services.recipient import get_opted_out_phones
from backend.services.google_sheets import sync_google_sheets

router = APIRouter(prefix="/api/recipients", tags=["Recipients"])

@router.get("", response_model=dict)
def list_recipients(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    consent: Optional[bool] = None,
    status: Optional[str] = None, # active | eligible | opted_out | deactivated
    db: Session = Depends(get_db)
):
    query = db.query(Recipient)
    opt_out_set = get_opted_out_phones(db)

    if search:
        s = f"%{search}%"
        query = query.filter(
            (Recipient.name.ilike(s)) | (Recipient.phone.ilike(s)) | (Recipient.email.ilike(s))
        )

    if consent is not None:
        query = query.filter(Recipient.consent == consent)

    all_recs = query.order_by(Recipient.id.desc()).all()

    results = []
    for r in all_recs:
        is_opted = r.phone in opt_out_set
        if status == "eligible" and (is_opted or not r.consent or r.status == "DEACTIVATED"):
            continue
        if status == "opted_out" and not is_opted:
            continue
        if status == "deactivated" and r.status != "DEACTIVATED":
            continue
        if status == "active" and (r.status == "DEACTIVATED" or is_opted):
            continue

        item = RecipientOut.model_validate(r)
        item.is_opted_out = is_opted
        results.append(item)

    total = len(results)
    start = (page - 1) * page_size
    end = start + page_size
    paginated = results[start:end]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": paginated
    }


@router.post("/sync", response_model=SyncReportOut, dependencies=[Depends(verify_bearer_token)])
def sync_recipients(db: Session = Depends(get_db)):
    try:
        report = sync_google_sheets(db, replace_all=False)
        return SyncReportOut(**report)
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=400,
            detail="Google Service Account key file missing at credentials/google-service-account.json. Please configure credentials."
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google Sheets sync failed: {str(e)}")


@router.post("/replace-from-sheet", response_model=SyncReportOut, dependencies=[Depends(verify_bearer_token)])
def replace_recipients_from_sheet(db: Session = Depends(get_db)):
    try:
        report = sync_google_sheets(db, replace_all=True)
        return SyncReportOut(**report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Replace recipients failed: {str(e)}")


@router.get("/{id}", response_model=RecipientOut)
def get_recipient(id: int, db: Session = Depends(get_db)):
    recipient = db.query(Recipient).filter(Recipient.id == id).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    
    opt_out_set = get_opted_out_phones(db)
    res = RecipientOut.model_validate(recipient)
    res.is_opted_out = recipient.phone in opt_out_set
    return res


@router.put("/{id}/deactivate", dependencies=[Depends(verify_bearer_token)])
def deactivate_recipient(id: int, db: Session = Depends(get_db)):
    recipient = db.query(Recipient).filter(Recipient.id == id).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    recipient.status = "DEACTIVATED"
    db.commit()
    return {"message": f"Recipient '{recipient.name}' deactivated. Local edit does not modify Google Sheet."}


@router.put("/{id}/activate", dependencies=[Depends(verify_bearer_token)])
def activate_recipient(id: int, db: Session = Depends(get_db)):
    recipient = db.query(Recipient).filter(Recipient.id == id).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    recipient.status = "ACTIVE"
    db.commit()
    return {"message": f"Recipient '{recipient.name}' activated."}
