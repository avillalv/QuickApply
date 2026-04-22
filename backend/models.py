from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class ResumeLabel(str, Enum):
    data_engineer = "Data Engineer"
    data_analyst = "Data Analyst"
    data_science = "Data Science"


class ProfileData(BaseModel):
    name: str
    email: str
    phone: str
    linkedin_url: str
    github_url: str
    portfolio_url: str
    city: str
    state: str
    zip_code: str
    us_citizen: bool
    work_authorized: bool
    sponsorship_needed: bool
    race_ethnicity: Optional[str] = None
    gender: Optional[str] = None
    veteran_status: Optional[str] = None
    disability_status: Optional[str] = None
    school: str
    degree: str
    major: str
    minor: Optional[str] = None
    gpa: Optional[str] = None
    graduation_date: Optional[str] = None
    experience: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of technology/skill to years of experience",
    )
    cover_letter_template: Optional[str] = None
    salary_expectation: Optional[str] = None
    start_date: Optional[str] = None
    willing_to_relocate: bool = False


class ResumeMetadata(BaseModel):
    id: Optional[str] = None
    label: str = Field(
        description="One of: Data Engineer, Data Analyst, Data Science"
    )
    file_name: str
    parsed_text: Optional[str] = None
    uploaded_at: Optional[str] = None


class JobAnalysis(BaseModel):
    match_score: int
    recommended_resume: str
    key_matches: list[str]
    gaps: list[str]
    apply_recommendation: str
    ats_platform: str
    estimated_apply_time: str


class ApplicationRecord(BaseModel):
    id: Optional[str] = None
    job_url: str
    company: Optional[str] = None
    job_title: Optional[str] = None
    location: Optional[str] = None
    salary_range: Optional[str] = None
    ats_platform: Optional[str] = None
    match_score: Optional[int] = None
    resume_used: Optional[str] = None
    status: str = "Applied"
    job_description: Optional[str] = None
    answers_given: Optional[dict] = None
    notes: Optional[str] = None
    applied_at: Optional[str] = None
    follow_up_date: Optional[str] = None
    last_status_update: Optional[str] = None


class ApplicationStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None
    follow_up_date: Optional[str] = None


class JobUrlRequest(BaseModel):
    url: str


class AutomationRequest(BaseModel):
    job_url: str
    mode: str = Field(description="Either 'full_auto' or 'copilot'")
    resume_label: str
    application_id: Optional[str] = None


class QuestionRequest(BaseModel):
    question: str
    job_title: str
    company: str
    job_description: str
    resume_text: str
    profile_summary: str


class SettingItem(BaseModel):
    key: str
    value: str
