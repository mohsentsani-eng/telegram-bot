"""Versioned, non-sensitive foundation endpoints for the Taranom Hamdeli mobile app.

Personal student data endpoints will be added only after the Telegram-based
account-verification and token lifecycle are implemented.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/mobile", tags=["mobile-app"])


@router.get("/health")
def mobile_health():
    """Lightweight connectivity check; contains no personal or deployment secrets."""
    return {"ok": True, "service": "taranom-mobile-api", "api_version": 1}


@router.get("/capabilities")
def mobile_capabilities():
    """Feature contract used by mobile clients to show supported app capabilities."""
    return {
        "api_version": 1,
        "minimum_client_version": "0.1.0",
        "roles": ["student", "parent", "counselor", "admin"],
        "offline": {
            "downloadable_study_plans": True,
            "downloadable_assessments": True,
            "assessment_answer_queue": True,
            "daily_report_queue": True,
            "mood_checkin_queue": True,
            "automatic_sync": True,
        },
        "online_only": [
            "live_messaging",
            "ai_analysis",
            "push_notification_delivery",
        ],
        "sync": {
            "protocol": "idempotent-operation-queue",
            "client_generated_operation_id": True,
            "conflict_policy": "server-authoritative-with-explicit-conflict-response",
        },
    }
