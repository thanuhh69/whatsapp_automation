from fastapi import APIRouter, Depends
from backend.schemas import WhatsAppStatusOut
from backend.auth import verify_bearer_token
from backend.services.whatsapp import whatsapp_service
from backend.services.whatsapp_inbox import inbox_poller

router = APIRouter(prefix="/api/whatsapp", tags=["WhatsApp"])

@router.get("/status", response_model=WhatsAppStatusOut)
def get_whatsapp_status():
    status = whatsapp_service.get_status()
    return WhatsAppStatusOut(
        status=status,
        qr_code_needed=(status in ["disconnected", "connecting"])
    )


@router.post("/connect", dependencies=[Depends(verify_bearer_token)])
async def connect_whatsapp():
    result = await whatsapp_service.connect()
    if result.get("status") == "connected":
        inbox_poller.start(whatsapp_service)
    return result


@router.post("/disconnect", dependencies=[Depends(verify_bearer_token)])
async def disconnect_whatsapp():
    inbox_poller.stop()
    result = await whatsapp_service.disconnect()
    return result


@router.post("/test-send", dependencies=[Depends(verify_bearer_token)])
async def test_send_whatsapp(payload: dict):
    phone = payload.get("phone", "").strip()
    message = payload.get("message", "").strip()
    if not phone or not message:
        return {"success": False, "error": "Phone number and test message are required.", "steps": []}
    
    from backend.services.recipient import normalize_phone
    norm_phone, valid = normalize_phone(phone)
    if not valid or not norm_phone:
        return {"success": False, "error": f"Invalid phone number '{phone}'", "steps": ["Phone number normalization failed"]}

    result = await whatsapp_service.send_test_message(norm_phone, message)
    return result
