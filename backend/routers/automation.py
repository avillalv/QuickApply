"""
Automation router — starts automation sessions and tracks their status.

POST /api/automation/start  → launches background task, returns session_id
GET  /api/automation/{id}   → returns session status
POST /api/automation/{id}/abort → aborts a running session
"""

import asyncio
import uuid

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

from database import get_supabase
from services.applicator import (
    AutomationSession,
    ApplicationAutomator,
    register_session,
    get_session,
)

router = APIRouter(prefix="/api/automation", tags=["automation"])


class StartAutomationRequest(BaseModel):
    job_url: str
    resume_label: str
    mode: str = "copilot"
    job_data: dict = {}
    application_id: Optional[str] = None


@router.post("/start")
async def start_automation(req: StartAutomationRequest):
    """
    Create an automation session and launch the Playwright task in background.
    Returns session_id for the frontend to connect its WebSocket.
    """
    sb = get_supabase()

    # Load profile
    profile_result = sb.table("profile").select("data").execute()
    profile = profile_result.data[0]["data"] if profile_result.data else {}

    # Load resumes
    resumes_result = sb.table("resumes").select("*").execute()
    resumes = resumes_result.data or []

    # Load settings
    settings_result = sb.table("settings").select("*").execute()
    settings = {row["key"]: row["value"] for row in (settings_result.data or [])}

    session_id = str(uuid.uuid4())
    session = AutomationSession(
        session_id=session_id,
        mode=req.mode,
        profile=profile,
        resumes=resumes,
        settings=settings,
    )
    register_session(session)

    automator = ApplicationAutomator(session)

    # Create a record if not already done
    app_id = req.application_id
    if not app_id:
        try:
            from datetime import datetime, timezone
            insert_data = {
                "job_url": req.job_url,
                "company": req.job_data.get("company", ""),
                "job_title": req.job_data.get("job_title", ""),
                "ats_platform": req.job_data.get("ats_platform", ""),
                "location": req.job_data.get("location", ""),
                "salary_range": req.job_data.get("salary_range", ""),
                "resume_used": req.resume_label,
                "status": "Applied",
                "job_description": req.job_data.get("job_description", "")[:5000],
                "applied_at": datetime.now(timezone.utc).isoformat(),
                "last_status_update": datetime.now(timezone.utc).isoformat(),
            }
            result = sb.table("applications").insert(insert_data).execute()
            if result.data:
                app_id = result.data[0]["id"]
        except Exception:
            pass

    # Launch the automation task (non-blocking)
    task = asyncio.create_task(
        automator.run(
            job_url=req.job_url,
            resume_label=req.resume_label,
            job_data=req.job_data,
            application_id=app_id or "",
        )
    )
    session.task = task

    return {
        "session_id": session_id,
        "application_id": app_id,
        "status": "starting",
    }


@router.get("/{session_id}")
async def get_automation_status(session_id: str):
    session = get_session(session_id)
    if not session:
        return {"session_id": session_id, "status": "not_found"}
    return {
        "session_id": session_id,
        "status": session.status,
        "current_page": session.current_page,
        "mode": session.mode,
        "created_at": session.created_at,
    }


@router.post("/{session_id}/abort")
async def abort_automation(session_id: str):
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await session.receive_from_client({"type": "abort"})
    return {"status": "abort_sent"}
