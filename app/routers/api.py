from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from app.models.schemas import VoiceQueryRequest, AdminLoginRequest
from app.models.database import get_properties, SUBDIVISIONS, get_access_logs
from app.services.portal_adapter import SUPPORTED_PORTALS
from app.services.voice_agent_service import voice_agent

router = APIRouter(prefix="/api/v1", tags=["FindHome Vietnam API"])

@router.get("/properties")
async def list_properties(
    city: Optional[str] = Query(None),
    subdivision: Optional[str] = Query(None),
    portal: Optional[str] = Query(None),
    min_bedrooms: Optional[int] = Query(None),
    max_total_rent: Optional[float] = Query(None)
):
    return get_properties(city=city, subdivision=subdivision, portal=portal, min_bedrooms=min_bedrooms, max_total_rent=max_total_rent)

@router.get("/portals")
async def get_portals():
    return SUPPORTED_PORTALS

@router.get("/subdivisions")
async def get_subdivisions():
    return SUBDIVISIONS

@router.post("/voice/query")
async def query_voice(payload: VoiceQueryRequest):
    return voice_agent.process_query(payload.query, lang=payload.lang, user_id="web_session", channel="web")

@router.post("/whatsapp/webhook")
async def whatsapp_webhook(payload: Dict[str, Any]):
    message_text = payload.get("message", payload.get("Body", payload.get("text", "")))
    sender_phone = payload.get("from", payload.get("From", payload.get("from_number", "WhatsApp Visitor")))
    sender_name = payload.get("name", payload.get("ProfileName", "Direct Inquiry"))

    result = voice_agent.process_query(
        message_text,
        lang=None,
        user_id=str(sender_phone),
        user_name=str(sender_name),
        channel="whatsapp"
    )
    reply_text = result.get("reply_text", "Thank you for contacting us.")
    try:
        from app.models.database import record_whatsapp_log
        record_whatsapp_log(str(sender_phone), str(sender_name), str(message_text), str(reply_text))
    except Exception:
        pass

    return {
        "status": "success",
        "sender": sender_phone,
        "reply": reply_text,
        "auto_reply": reply_text,
        "action": result.get("action"),
        "whatsapp_url": result.get("whatsapp_url")
    }

@router.post("/admin/login")
async def admin_login(payload: AdminLoginRequest):
    if payload.password == "admin123":
        return {"authenticated": True, "status": "authenticated"}
    raise HTTPException(status_code=401, detail="Unauthorized")

@router.get("/admin/access-logs")
async def admin_logs():
    return get_access_logs(100)

@router.get("/admin/stats")
async def admin_stats():
    logs = get_access_logs(200)
    return {"total_visits": len(logs), "unique_countries": len(set(l.get("country", "") for l in logs if l.get("country"))), "unique_cities": len(set(l.get("city", "") for l in logs if l.get("city")))}
