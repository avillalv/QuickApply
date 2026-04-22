"""
Claude API-powered job analyzer.

Analyzes a job posting against the user's resumes and returns a structured
JobAnalysis including match score, recommended resume, gaps, and apply advice.
"""

import json
import os
import re

import anthropic
from dotenv import load_dotenv

load_dotenv()

_MODEL = "claude-sonnet-4-20250514"

_DEFAULT_ANALYSIS = {
    "match_score": 0,
    "recommended_resume": "",
    "key_matches": [],
    "gaps": [],
    "apply_recommendation": "Unable to analyze — please try again.",
    "ats_platform": "Unknown",
    "estimated_apply_time": "Unknown",
}


def _build_prompt(job_data: dict, resumes: list[dict]) -> str:
    """Build the analysis prompt sent to Claude."""
    job_title = job_data.get("job_title", "Unknown Role")
    company = job_data.get("company", "Unknown Company")
    job_description = job_data.get("job_description", "")
    ats_platform = job_data.get("ats_platform", "Unknown")

    resume_sections = []
    for resume in resumes:
        label = resume.get("label", "Resume")
        text = resume.get("parsed_text", "") or ""
        resume_sections.append(f"--- {label} ---\n{text[:3000]}")

    resumes_block = "\n\n".join(resume_sections) if resume_sections else "No resumes provided."

    prompt = f"""You are an expert job application coach and ATS specialist.

Analyze the following job posting and the applicant's resumes, then return a JSON object matching the schema below.

## Job Posting
**Title**: {job_title}
**Company**: {company}
**ATS Platform**: {ats_platform}

**Job Description**:
{job_description[:4000]}

## Applicant Resumes
{resumes_block}

## Instructions
1. Calculate a match_score (0–100) based on how well the best resume matches the job requirements.
2. Identify which resume label best fits this role.
3. List concrete key_matches (skills/tools/experiences the applicant has that the job requires).
4. List gaps (skills/tools the job requires that are missing from the resumes).
5. Write a short, direct apply_recommendation (1–2 sentences on what to lead with or watch out for).
6. Confirm or correct the ats_platform based on the job description context.
7. Estimate the apply_time in minutes based on the ATS complexity.

Return ONLY valid JSON — no markdown fences, no extra text — matching this exact schema:
{{
  "match_score": <integer 0-100>,
  "recommended_resume": "<one of the resume labels provided>",
  "key_matches": ["<skill or tool>", ...],
  "gaps": ["<missing skill or tool>", ...],
  "apply_recommendation": "<concise advice string>",
  "ats_platform": "<platform name>",
  "estimated_apply_time": "<e.g. '8 minutes'>"
}}"""

    return prompt


def _extract_json(text: str) -> dict:
    """
    Attempt to parse a JSON object from Claude's response text.
    Handles cases where Claude wraps JSON in markdown code fences.
    """
    # Strip markdown fences if present
    text = text.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if fence_match:
        text = fence_match.group(1).strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find a JSON object via regex
    obj_match = re.search(r"\{[\s\S]+\}", text)
    if obj_match:
        try:
            return json.loads(obj_match.group(0))
        except json.JSONDecodeError:
            pass

    return {}


async def analyze_job(job_data: dict, resumes: list[dict]) -> dict:
    """
    Analyze a job posting against the provided resumes using Claude.

    Args:
        job_data: Dict with keys from scraper (job_title, company,
                  job_description, ats_platform, etc.).
        resumes:  List of resume dicts, each with 'label' and 'parsed_text'.

    Returns:
        Dict matching the JobAnalysis schema, or defaults with match_score=0
        if analysis fails.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        result = dict(_DEFAULT_ANALYSIS)
        result["apply_recommendation"] = "ANTHROPIC_API_KEY is not set."
        return result

    client = anthropic.Anthropic(api_key=api_key)
    prompt = _build_prompt(job_data, resumes)

    try:
        message = client.messages.create(
            model=_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = message.content[0].text if message.content else ""
        parsed = _extract_json(response_text)

        if not parsed or "match_score" not in parsed:
            return dict(_DEFAULT_ANALYSIS)

        # Validate and normalise fields
        analysis = dict(_DEFAULT_ANALYSIS)
        analysis["match_score"] = int(parsed.get("match_score", 0))
        analysis["recommended_resume"] = str(parsed.get("recommended_resume", ""))
        analysis["key_matches"] = [str(x) for x in parsed.get("key_matches", [])]
        analysis["gaps"] = [str(x) for x in parsed.get("gaps", [])]
        analysis["apply_recommendation"] = str(parsed.get("apply_recommendation", ""))
        analysis["ats_platform"] = str(
            parsed.get("ats_platform", job_data.get("ats_platform", "Unknown"))
        )
        analysis["estimated_apply_time"] = str(parsed.get("estimated_apply_time", "Unknown"))

        return analysis

    except anthropic.APIError as exc:
        result = dict(_DEFAULT_ANALYSIS)
        result["apply_recommendation"] = f"API error: {exc}"
        return result
    except Exception as exc:
        result = dict(_DEFAULT_ANALYSIS)
        result["apply_recommendation"] = f"Unexpected error: {exc}"
        return result
