from fastapi import APIRouter, HTTPException

from database import get_supabase
from models import JobUrlRequest
from services.scraper import scrape_job_posting
from services.analyzer import analyze_job

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

ATS_PLATFORMS = [
    "Workday", "Greenhouse", "Lever", "iCIMS", "Taleo",
    "SmartRecruiters", "Ashby", "BambooHR", "JazzHR", "ADP", "Custom ATS",
]


@router.post("/analyze")
async def analyze_job_posting(request: JobUrlRequest):
    try:
        job_data = await scrape_job_posting(request.url)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Failed to scrape job posting: {exc}")

    sb = get_supabase()
    resumes_result = sb.table("resumes").select("label, parsed_text").execute()
    resumes = resumes_result.data or []

    try:
        analysis = await analyze_job(job_data, resumes)
    except Exception as exc:
        analysis = {
            "match_score": 0,
            "recommended_resume": "",
            "key_matches": [],
            "gaps": [],
            "apply_recommendation": f"Analysis failed: {exc}",
            "ats_platform": job_data.get("ats_platform", "Unknown"),
            "estimated_apply_time": "Unknown",
        }

    return {"job_data": job_data, "analysis": analysis}


@router.get("/ats-platforms")
async def get_ats_platforms():
    return {"platforms": ATS_PLATFORMS}
