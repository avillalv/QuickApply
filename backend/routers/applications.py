import csv
import io
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from database import get_supabase
from models import ApplicationRecord, ApplicationStatusUpdate

router = APIRouter(prefix="/api/applications", tags=["applications"])


@router.get("/stats/summary")
async def get_stats():
    sb = get_supabase()
    result = sb.table("applications").select("*").execute()
    apps = result.data or []

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    total = len(apps)
    this_week = sum(
        1 for a in apps
        if a.get("applied_at") and _parse_dt(a["applied_at"]) >= week_ago
    )

    scores = [a["match_score"] for a in apps if a.get("match_score") is not None]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

    responded = sum(
        1 for a in apps
        if a.get("status") in ("Phone Screen", "Interview", "Offer")
    )
    response_rate = round((responded / total * 100), 1) if total else 0.0

    by_status: dict[str, int] = {}
    for a in apps:
        s = a.get("status", "Applied")
        by_status[s] = by_status.get(s, 0) + 1

    return {
        "total": total,
        "this_week": this_week,
        "avg_match_score": avg_score,
        "response_rate": response_rate,
        "by_status": by_status,
    }


@router.get("/export/csv")
async def export_csv():
    sb = get_supabase()
    result = sb.table("applications").select("*").order("applied_at", desc=True).execute()
    apps = result.data or []

    columns = [
        "applied_at", "company", "job_title", "ats_platform", "match_score",
        "resume_used", "status", "location", "salary_range", "notes",
        "follow_up_date", "job_url",
    ]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for app in apps:
        writer.writerow({k: app.get(k, "") for k in columns})

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=applications.csv"},
    )


@router.get("")
async def list_applications(
    status: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("applied_at"),
    sort_desc: bool = Query(True),
):
    sb = get_supabase()
    query = sb.table("applications").select("*")
    if status:
        query = query.eq("status", status)
    query = query.order(sort_by or "applied_at", desc=sort_desc)
    result = query.execute()
    return result.data or []


@router.post("")
async def create_application(app: ApplicationRecord):
    sb = get_supabase()
    data = app.model_dump(exclude_none=True, exclude={"id"})
    if "applied_at" not in data:
        data["applied_at"] = datetime.now(timezone.utc).isoformat()
    if "last_status_update" not in data:
        data["last_status_update"] = datetime.now(timezone.utc).isoformat()
    result = sb.table("applications").insert(data).execute()
    return result.data[0] if result.data else data


@router.get("/{app_id}")
async def get_application(app_id: str):
    sb = get_supabase()
    result = sb.table("applications").select("*").eq("id", app_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Application not found")
    return result.data[0]


@router.patch("/{app_id}")
async def update_application(app_id: str, update: ApplicationStatusUpdate):
    sb = get_supabase()
    data: dict = {"last_status_update": datetime.now(timezone.utc).isoformat()}
    if update.status:
        data["status"] = update.status
    if update.notes is not None:
        data["notes"] = update.notes
    if update.follow_up_date is not None:
        data["follow_up_date"] = update.follow_up_date
    result = sb.table("applications").update(data).eq("id", app_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Application not found")
    return result.data[0]


@router.delete("/{app_id}")
async def delete_application(app_id: str):
    sb = get_supabase()
    sb.table("applications").delete().eq("id", app_id).execute()
    return {"status": "deleted"}


def _parse_dt(val: str) -> datetime:
    try:
        dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)
