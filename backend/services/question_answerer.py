"""
Question answerer — Claude-powered when AI is enabled, template-based otherwise.
"""
import os
import re

_MODEL = "claude-sonnet-4-20250514"

# ---------------------------------------------------------------------------
# Profile summary
# ---------------------------------------------------------------------------

def build_profile_summary(profile: dict) -> str:
    lines: list[str] = []

    name = profile.get("name", "")
    if name:
        lines.append(f"Name: {name}")

    for key, label in [
        ("email", "Email"), ("phone", "Phone"),
        ("linkedin_url", "LinkedIn"), ("github_url", "GitHub"),
        ("portfolio_url", "Portfolio"),
    ]:
        if profile.get(key):
            lines.append(f"{label}: {profile[key]}")

    city, state, zip_code = profile.get("city",""), profile.get("state",""), profile.get("zip_code","")
    loc = ", ".join(p for p in [city, state, zip_code] if p)
    if loc:
        lines.append(f"Location: {loc}")

    for key, label in [("school","School"), ("degree","Degree"), ("major","Major"), ("gpa","GPA")]:
        if profile.get(key):
            lines.append(f"{label}: {profile[key]}")

    exp = profile.get("experience", {})
    if exp:
        lines.append("Technical Experience: " + ", ".join(f"{k} ({v})" for k,v in exp.items()))

    for key, label in [
        ("us_citizen","US Citizen"), ("work_authorized","Work Authorized"),
        ("sponsorship_needed","Needs Sponsorship"),
    ]:
        val = profile.get(key)
        if val is not None:
            lines.append(f"{label}: {'Yes' if val else 'No'}")

    if profile.get("salary_expectation"):
        lines.append(f"Salary Expectation: {profile['salary_expectation']}")
    if profile.get("start_date"):
        lines.append(f"Start Date: {profile['start_date']}")
    if profile.get("willing_to_relocate") is not None:
        lines.append(f"Willing to Relocate: {'Yes' if profile['willing_to_relocate'] else 'No'}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Common question templates (no AI required)
# ---------------------------------------------------------------------------

def answer_common_question(question_type: str, profile: dict, job_data: dict) -> str:
    """Return a profile-based answer for standard application questions."""
    qt = question_type.lower().strip()
    company = job_data.get("company", "the company")
    job_title = job_data.get("job_title", "this role")

    if qt == "work_authorization":
        if profile.get("us_citizen"):
            return "Yes"
        if profile.get("work_authorized"):
            return "Yes"
        return "No"

    if qt == "sponsorship":
        return "Yes" if profile.get("sponsorship_needed") else "No"

    if qt == "salary":
        s = profile.get("salary_expectation", "")
        if s:
            return s
        return "Open to competitive offer"

    if qt == "start_date":
        d = profile.get("start_date", "")
        return d if d else "2 weeks after offer"

    if qt == "relocation":
        return "Yes" if profile.get("willing_to_relocate") else "No"

    if qt == "hear_about":
        return "Job board search"

    if qt == "why_interested":
        name = profile.get("name", "").split()[0] or "I"
        exp = profile.get("experience", {})
        top_skills = list(exp.keys())[:3]
        skills_str = ", ".join(top_skills) if top_skills else "data engineering"
        return (
            f"I am drawn to this {job_title} role because it aligns directly with my "
            f"background in {skills_str}. {company}'s focus on data-driven decisions "
            f"matches the kind of work I want to be doing."
        )

    if qt == "cover_letter":
        template = profile.get("cover_letter_template", "")
        if template:
            return (
                template
                .replace("{company}", company)
                .replace("{job_title}", job_title)
                .replace("{{company}}", company)
                .replace("{{job_title}}", job_title)
            )
        name = profile.get("name", "")
        return (
            f"Dear Hiring Team,\n\n"
            f"I am excited to apply for the {job_title} position at {company}. "
            f"My experience in data engineering and analytics makes me a strong fit "
            f"for this role. I look forward to the opportunity to contribute.\n\n"
            f"Best regards,\n{name}"
        )

    return ""


# ---------------------------------------------------------------------------
# Template-based answers for open-ended questions (no AI)
# ---------------------------------------------------------------------------

_COMMON_PATTERNS = [
    (r"authorized.*(work|us|united states)", "work_authorization"),
    (r"work.*(authorization|auth|permit)", "work_authorization"),
    (r"(require|need).*(sponsor|visa)", "sponsorship"),
    (r"sponsor", "sponsorship"),
    (r"(salary|compensation|pay).*(expect|requir|want|desire)", "salary"),
    (r"start.?date|available.*(start|begin)|earliest", "start_date"),
    (r"relocat", "relocation"),
    (r"hear.*(about|of|this)", "hear_about"),
    (r"why.*(interest|apply|want|this role|position)", "why_interested"),
    (r"cover.?letter", "cover_letter"),
]


def _detect_question_type(question: str) -> str | None:
    q = question.lower()
    for pattern, qtype in _COMMON_PATTERNS:
        if re.search(pattern, q):
            return qtype
    return None


def answer_question_no_ai(question: str, profile: dict, job_data: dict) -> str:
    """Answer a question using templates only — no API call."""
    qtype = _detect_question_type(question)
    if qtype:
        answer = answer_common_question(qtype, profile, job_data)
        if answer:
            return answer

    # Fallback: check if question mentions a technology from profile.experience
    exp = profile.get("experience", {})
    q_lower = question.lower()
    for tech, years in exp.items():
        if tech.lower() in q_lower:
            return f"{years} of experience"

    return ""


# ---------------------------------------------------------------------------
# Claude-powered answerer
# ---------------------------------------------------------------------------

async def answer_question(
    question: str,
    job_title: str,
    company: str,
    job_description: str,
    resume_text: str,
    profile_summary: str,
    use_ai: bool = True,
) -> str:
    """
    Generate an answer to a job application question.

    If use_ai=False or ANTHROPIC_API_KEY not set, uses template-based answering.
    """
    if not use_ai:
        return ""

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return ""

    import anthropic

    prompt = (
        f"You are filling out a job application for {job_title} at {company}.\n"
        f"Job description: {job_description[:1500]}\n"
        f"Applicant resume: {resume_text[:1500]}\n"
        f"Applicant profile: {profile_summary}\n\n"
        "Answer this application question concisely and authentically. "
        "Do not use em dashes. Do not sound like AI. Be direct and specific. "
        "Use concrete examples from the resume when relevant. "
        "Keep answers under 200 words.\n\n"
        f"Question: {question}"
    )

    client = anthropic.Anthropic(api_key=api_key)
    try:
        msg = client.messages.create(
            model=_MODEL,
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip() if msg.content else ""
    except Exception:
        return ""
