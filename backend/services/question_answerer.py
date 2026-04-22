"""
Claude API-powered question answerer for job application forms.

Provides:
- answer_question()         — full Claude-powered answer for open-ended questions
- answer_common_question()  — fast profile-based answers for simple factual questions
- build_profile_summary()   — converts a profile dict to a readable summary string
"""

import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

_MODEL = "claude-sonnet-4-20250514"


def build_profile_summary(profile: dict) -> str:
    """
    Convert a profile dict into a readable plain-text summary
    suitable for inclusion in a Claude prompt.
    """
    lines: list[str] = []

    name = profile.get("name", "")
    if name:
        lines.append(f"Name: {name}")

    email = profile.get("email", "")
    if email:
        lines.append(f"Email: {email}")

    phone = profile.get("phone", "")
    if phone:
        lines.append(f"Phone: {phone}")

    location_parts = [
        profile.get("city", ""),
        profile.get("state", ""),
        profile.get("zip_code", ""),
    ]
    location = ", ".join(p for p in location_parts if p)
    if location:
        lines.append(f"Location: {location}")

    school = profile.get("school", "")
    degree = profile.get("degree", "")
    major = profile.get("major", "")
    if school or degree or major:
        edu_parts = [p for p in [degree, major, school] if p]
        lines.append(f"Education: {', '.join(edu_parts)}")

    gpa = profile.get("gpa", "")
    if gpa:
        lines.append(f"GPA: {gpa}")

    graduation_date = profile.get("graduation_date", "")
    if graduation_date:
        lines.append(f"Graduation: {graduation_date}")

    experience: dict = profile.get("experience", {})
    if experience:
        exp_parts = [f"{tech} ({yrs} yrs)" for tech, yrs in experience.items()]
        lines.append(f"Technical Experience: {', '.join(exp_parts)}")

    linkedin = profile.get("linkedin_url", "")
    if linkedin:
        lines.append(f"LinkedIn: {linkedin}")

    github = profile.get("github_url", "")
    if github:
        lines.append(f"GitHub: {github}")

    portfolio = profile.get("portfolio_url", "")
    if portfolio:
        lines.append(f"Portfolio: {portfolio}")

    us_citizen = profile.get("us_citizen")
    work_auth = profile.get("work_authorized")
    sponsorship = profile.get("sponsorship_needed")
    if us_citizen is not None:
        lines.append(f"US Citizen: {'Yes' if us_citizen else 'No'}")
    if work_auth is not None:
        lines.append(f"Authorized to Work in US: {'Yes' if work_auth else 'No'}")
    if sponsorship is not None:
        lines.append(f"Requires Sponsorship: {'Yes' if sponsorship else 'No'}")

    salary = profile.get("salary_expectation", "")
    if salary:
        lines.append(f"Salary Expectation: {salary}")

    start_date = profile.get("start_date", "")
    if start_date:
        lines.append(f"Available Start Date: {start_date}")

    relocate = profile.get("willing_to_relocate")
    if relocate is not None:
        lines.append(f"Willing to Relocate: {'Yes' if relocate else 'No'}")

    return "\n".join(lines)


def answer_common_question(
    question_type: str,
    profile: dict,
    job_data: dict,
) -> str:
    """
    Return a direct, profile-based answer for common factual application
    questions without calling the Claude API.

    Args:
        question_type: One of "work_authorization", "sponsorship", "salary",
                       "start_date", "relocation", "hear_about".
        profile:       The applicant's profile dict.
        job_data:      The scraped job data dict.

    Returns:
        A concise answer string.
    """
    qt = question_type.lower().strip()

    if qt == "work_authorization":
        if profile.get("us_citizen"):
            return "Yes, I am a US citizen and fully authorized to work in the United States."
        if profile.get("work_authorized"):
            return "Yes, I am authorized to work in the United States."
        return "I am not currently authorized to work in the United States without sponsorship."

    if qt == "sponsorship":
        if profile.get("sponsorship_needed"):
            return "Yes, I will require employer sponsorship in the future."
        return "No, I do not require sponsorship now or in the future."

    if qt == "salary":
        salary = profile.get("salary_expectation", "")
        if salary:
            return f"My salary expectation is {salary}, though I am open to discussion based on the full compensation package."
        return "I am open to a competitive offer commensurate with the role and my experience."

    if qt == "start_date":
        start_date = profile.get("start_date", "")
        if start_date:
            return f"I am available to start on {start_date}."
        return "I am available to start within two weeks of receiving an offer."

    if qt == "relocation":
        if profile.get("willing_to_relocate"):
            return "Yes, I am open to relocation."
        city = profile.get("city", "")
        state = profile.get("state", "")
        location = f"{city}, {state}".strip(", ")
        if location:
            return f"I am currently based in {location} and am not looking to relocate at this time."
        return "I am not currently looking to relocate."

    if qt == "hear_about":
        company = job_data.get("company", "the company")
        return (
            f"I came across this opportunity while researching data engineering roles and "
            f"was drawn to {company}'s work. The position aligns well with my background "
            f"and career goals."
        )

    return ""


async def answer_question(
    question: str,
    job_title: str,
    company: str,
    job_description: str,
    resume_text: str,
    profile_summary: str,
) -> str:
    """
    Use Claude to generate a concise, authentic answer to a job application
    question.

    Args:
        question:        The application question to answer.
        job_title:       The role being applied for.
        company:         The hiring company.
        job_description: Full text of the job description.
        resume_text:     Parsed text of the applicant's resume.
        profile_summary: Output of build_profile_summary().

    Returns:
        The answer string, or an error message if the API call fails.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return "[Error: ANTHROPIC_API_KEY is not configured.]"

    system_prompt = (
        f"You are filling out a job application for {job_title} at {company}.\n"
        f"Here is the job description: {job_description[:2000]}\n"
        f"Here is the applicant's resume: {resume_text[:2000]}\n"
        f"Here is the applicant's profile: {profile_summary}\n\n"
        "Answer this application question concisely and authentically.\n"
        "Do not use em dashes. Do not sound like AI. Be direct and specific.\n"
        "Use concrete examples from the resume when relevant.\n"
        "Keep answers under 200 words unless the field allows more.\n\n"
        f"Question: {question}"
    )

    client = anthropic.Anthropic(api_key=api_key)

    try:
        message = client.messages.create(
            model=_MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": system_prompt}],
        )
        if message.content:
            return message.content[0].text.strip()
        return ""
    except anthropic.APIError as exc:
        return f"[API error: {exc}]"
    except Exception as exc:
        return f"[Error generating answer: {exc}]"
