"""
Job analyzer — Claude-powered when AI is enabled, keyword-based fallback otherwise.
"""
import json
import os
import re

_MODEL = "claude-sonnet-4-20250514"

_DEFAULT = {
    "match_score": 0,
    "recommended_resume": "",
    "key_matches": [],
    "gaps": [],
    "apply_recommendation": "Analysis unavailable.",
    "ats_platform": "Unknown",
    "estimated_apply_time": "~10 minutes",
}

# Common data engineering / analyst keywords for fallback scoring
_TECH_KEYWORDS = [
    "python", "sql", "spark", "kafka", "airflow", "dbt", "dbt core",
    "snowflake", "bigquery", "redshift", "databricks", "pyspark",
    "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch",
    "aws", "gcp", "azure", "s3", "ec2", "lambda", "glue", "athena",
    "power bi", "tableau", "looker", "metabase",
    "postgres", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "docker", "kubernetes", "terraform", "ci/cd", "git",
    "etl", "elt", "data pipeline", "data warehouse", "data lake",
    "machine learning", "ml", "deep learning", "nlp",
    "excel", "r", "scala", "java", "go", "typescript",
]


def _extract_keywords(text: str) -> set[str]:
    text_lower = text.lower()
    found = set()
    for kw in _TECH_KEYWORDS:
        if kw in text_lower:
            found.add(kw)
    return found


def _keyword_analyze(job_data: dict, resumes: list[dict]) -> dict:
    """Offline keyword-matching analysis — no API call."""
    jd = (job_data.get("job_description") or "").lower()
    jd_keywords = _extract_keywords(jd)

    best_label = ""
    best_score = 0
    best_matches: list[str] = []
    all_resume_keywords: set[str] = set()

    for resume in resumes:
        text = (resume.get("parsed_text") or "").lower()
        resume_kws = _extract_keywords(text)
        all_resume_keywords |= resume_kws
        matched = jd_keywords & resume_kws
        score = round(len(matched) / max(len(jd_keywords), 1) * 100)
        if score > best_score:
            best_score = score
            best_label = resume.get("label", "")
            best_matches = sorted(matched)

    gaps = sorted(jd_keywords - all_resume_keywords)
    best_score = min(best_score, 95)

    if best_score >= 80:
        rec = "Strong match. Lead with directly relevant pipeline and analytics experience."
    elif best_score >= 60:
        rec = "Decent match. Highlight transferable skills and address gaps in your cover letter."
    else:
        rec = "Partial match. Review gaps before applying."

    ats = job_data.get("ats_platform", "Unknown")
    apply_times = {
        "Workday": "12 minutes",
        "Greenhouse": "7 minutes",
        "Lever": "6 minutes",
        "iCIMS": "10 minutes",
        "Taleo": "15 minutes",
    }

    return {
        "match_score": best_score,
        "recommended_resume": best_label,
        "key_matches": best_matches[:10],
        "gaps": gaps[:8],
        "apply_recommendation": rec,
        "ats_platform": ats,
        "estimated_apply_time": apply_times.get(ats, "~10 minutes"),
    }


def _extract_json(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    obj = re.search(r"\{[\s\S]+\}", text)
    if obj:
        try:
            return json.loads(obj.group(0))
        except json.JSONDecodeError:
            pass
    return {}


async def analyze_job(job_data: dict, resumes: list[dict], use_ai: bool = True) -> dict:
    """
    Analyze a job posting against the provided resumes.

    Args:
        job_data:  Dict from scraper.
        resumes:   List of resume dicts with 'label' and 'parsed_text'.
        use_ai:    If False, use offline keyword matching (no API cost).

    Returns:
        Dict matching the JobAnalysis schema.
    """
    if not use_ai:
        return _keyword_analyze(job_data, resumes)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return _keyword_analyze(job_data, resumes)

    import anthropic

    job_title = job_data.get("job_title", "Unknown Role")
    company = job_data.get("company", "Unknown Company")
    job_description = job_data.get("job_description", "")
    ats = job_data.get("ats_platform", "Unknown")

    resume_sections = "\n\n".join(
        f"--- {r.get('label', 'Resume')} ---\n{(r.get('parsed_text') or '')[:3000]}"
        for r in resumes
    ) or "No resumes provided."

    prompt = f"""You are an expert job application coach.

Analyze the job posting and applicant resumes below, then return ONLY a valid JSON object.

## Job Posting
Title: {job_title}
Company: {company}
ATS: {ats}

Description:
{job_description[:4000]}

## Applicant Resumes
{resume_sections}

## Instructions
Return ONLY this JSON (no markdown fences, no extra text):
{{
  "match_score": <integer 0-100>,
  "recommended_resume": "<one of the resume labels above>",
  "key_matches": ["<skill>", ...],
  "gaps": ["<missing skill>", ...],
  "apply_recommendation": "<1-2 sentence concise advice>",
  "ats_platform": "{ats}",
  "estimated_apply_time": "<e.g. '8 minutes'>"
}}"""

    client = anthropic.Anthropic(api_key=api_key)
    try:
        message = client.messages.create(
            model=_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text if message.content else ""
        parsed = _extract_json(text)
        if not parsed or "match_score" not in parsed:
            return _keyword_analyze(job_data, resumes)

        result = dict(_DEFAULT)
        result.update({
            "match_score": int(parsed.get("match_score", 0)),
            "recommended_resume": str(parsed.get("recommended_resume", "")),
            "key_matches": [str(x) for x in parsed.get("key_matches", [])],
            "gaps": [str(x) for x in parsed.get("gaps", [])],
            "apply_recommendation": str(parsed.get("apply_recommendation", "")),
            "ats_platform": str(parsed.get("ats_platform", ats)),
            "estimated_apply_time": str(parsed.get("estimated_apply_time", "~10 minutes")),
        })
        return result
    except Exception:
        return _keyword_analyze(job_data, resumes)
