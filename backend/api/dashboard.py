from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Recipient, Campaign, OptOut
from backend.schemas import DashboardStatsOut
from backend.services.recipient import get_eligible_recipients
from backend.services.whatsapp import whatsapp_service
from backend.config import settings

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/stats", response_model=DashboardStatsOut)
def get_dashboard_stats(db: Session = Depends(get_db)):
    total_registrants = db.query(Recipient).count()
    eligible = get_eligible_recipients(db)
    total_campaigns = db.query(Campaign).count()
    opt_out_count = db.query(OptOut).count()
    status = whatsapp_service.get_status()

    return DashboardStatsOut(
        total_registrants=total_registrants,
        eligible_recipients=len(eligible),
        total_campaigns=total_campaigns,
        opt_out_count=opt_out_count,
        whatsapp_status=status,
        test_mode_enabled=settings.TEST_MODE
    )
