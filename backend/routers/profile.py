import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse

from database import get_supabase
from models import ProfileData
from utils.resume_parser import parse_resume_pdf

router = APIRouter(prefix="/api/profile", tags=["profile"])

PROFILE_ID = "00000000-0000-0000-0000-000000000001"
RESUMES_DIR = Path(__file__).parent.parent.parent / "resumes"
RESUMES_DIR.mkdir(exist_ok=True)


@router.get("")
async def get_profile():
    sb = get_supabase()
    result = sb.table("profile").select("*").eq("id", PROFILE_ID).execute()
    if not result.data:
        return {}
    return result.data[0].get("data", {})


@router.put("")
async def update_profile(profile_data: dict):
    sb = get_supabase()
    sb.table("profile").upsert({
        "id": PROFILE_ID,
        "data": profile_data,
    }).execute()
    return {"status": "ok"}


@router.get("/resumes")
async def list_resumes():
    sb = get_supabase()
    result = sb.table("resumes").select("*").order("uploaded_at", desc=False).execute()
    return result.data or []


@router.post("/resumes/upload")
async def upload_resume(
    file: UploadFile = File(...),
    label: str = Form(...),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    safe_name = label.replace(" ", "_") + ".pdf"
    file_path = RESUMES_DIR / safe_name

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    parsed_text = parse_resume_pdf(str(file_path))

    sb = get_supabase()
    sb.table("resumes").upsert({
        "label": label,
        "file_name": safe_name,
        "parsed_text": parsed_text,
    }, on_conflict="label").execute()

    result = sb.table("resumes").select("*").eq("label", label).execute()
    return result.data[0] if result.data else {"label": label, "file_name": safe_name}


@router.delete("/resumes/{label}")
async def delete_resume(label: str):
    sb = get_supabase()
    result = sb.table("resumes").select("file_name").eq("label", label).execute()
    if result.data:
        file_path = RESUMES_DIR / result.data[0]["file_name"]
        if file_path.exists():
            file_path.unlink()
    sb.table("resumes").delete().eq("label", label).execute()
    return {"status": "deleted"}
