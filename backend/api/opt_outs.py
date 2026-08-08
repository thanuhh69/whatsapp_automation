from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.database import get_db
from backend.models import OptOut
from backend.schemas import OptOutOut, OptOutCreate
from backend.auth import verify_bearer_token
from backend.services.recipient import normalize_phone

router = APIRouter(prefix="/api/opt-outs", tags=["Opt-Outs"])

@router.get("", response_model=List[OptOutOut])
def list_opt_outs(db: Session = Depends(get_db)):
    return db.query(OptOut).order_by(OptOut.id.desc()).all()


@router.post("", response_model=OptOutOut, dependencies=[Depends(verify_bearer_token)])
def add_opt_out(payload: OptOutCreate, db: Session = Depends(get_db)):
    normalized, is_valid = normalize_phone(payload.phone)
    if not is_valid or not normalized:
        raise HTTPException(status_code=400, detail=f"Invalid phone number format: '{payload.phone}'")

    existing = db.query(OptOut).filter(OptOut.phone == normalized).first()
    if existing:
        return existing

    opt = OptOut(
        phone=normalized,
        reason=payload.reason or "Manual admin opt-out",
        source=payload.source or "manual"
    )
    db.add(opt)
    db.commit()
    db.refresh(opt)
    return opt


@router.delete("/{id}", dependencies=[Depends(verify_bearer_token)])
def delete_opt_out(id: int, db: Session = Depends(get_db)):
    opt = db.query(OptOut).filter(OptOut.id == id).first()
    if not opt:
        raise HTTPException(status_code=404, detail="Opt-out record not found")

    db.delete(opt)
    db.commit()
    return {"message": f"Opt-out record {id} removed"}
