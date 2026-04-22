import re
from typing import Optional
from difflib import SequenceMatcher


# Maps profile data keys to lists of common form field patterns (lowercased).
# Each entry is (profile_key, [pattern, ...]).
FIELD_MAPPINGS: dict[str, list[str]] = {
    "first_name": [
        "first name", "first", "fname", "given name", "forename",
    ],
    "last_name": [
        "last name", "last", "lname", "surname", "family name",
    ],
    "full_name": [
        "full name", "name", "your name", "legal name", "applicant name",
        "candidate name",
    ],
    "email": [
        "email", "e-mail", "email address", "work email", "personal email",
    ],
    "phone": [
        "phone", "phone number", "mobile", "mobile number", "cell",
        "cell phone", "telephone", "contact number",
    ],
    "linkedin_url": [
        "linkedin", "linkedin url", "linkedin profile", "linkedin profile url",
    ],
    "github_url": [
        "github", "github url", "github profile", "github profile url",
    ],
    "portfolio_url": [
        "portfolio", "portfolio url", "website", "personal website",
        "personal site",
    ],
    "city": [
        "city", "city of residence", "current city",
    ],
    "state": [
        "state", "state of residence", "province",
    ],
    "zip_code": [
        "zip", "zip code", "postal code", "postcode",
    ],
    "address": [
        "address", "street address", "mailing address", "home address",
        "current address",
    ],
    "work_authorized": [
        "authorized to work", "work authorization", "authorized",
        "legally authorized", "eligible to work", "work eligibility",
    ],
    "sponsorship_needed": [
        "sponsorship", "require sponsorship", "visa sponsorship",
        "need sponsorship", "immigration sponsorship",
    ],
    "us_citizen": [
        "us citizen", "united states citizen", "citizen", "citizenship",
    ],
    "salary_expectation": [
        "salary", "salary expectation", "expected salary",
        "desired salary", "compensation", "desired compensation",
        "salary requirement",
    ],
    "start_date": [
        "start date", "available start date", "earliest start date",
        "when can you start", "availability",
    ],
    "willing_to_relocate": [
        "relocate", "willing to relocate", "relocation", "open to relocation",
    ],
    "school": [
        "school", "university", "college", "institution", "alma mater",
        "school name", "university name",
    ],
    "degree": [
        "degree", "highest degree", "highest level of education",
        "education level", "degree type",
    ],
    "major": [
        "major", "field of study", "area of study", "concentration",
        "study major",
    ],
    "gpa": [
        "gpa", "grade point average", "cumulative gpa",
    ],
    "graduation_date": [
        "graduation date", "graduation year", "expected graduation",
        "date of graduation",
    ],
    "race_ethnicity": [
        "race", "ethnicity", "race/ethnicity", "racial identity",
        "ethnic background",
    ],
    "gender": [
        "gender", "gender identity", "sex",
    ],
    "veteran_status": [
        "veteran", "veteran status", "military service", "military status",
    ],
    "disability_status": [
        "disability", "disability status", "disabled",
    ],
    "cover_letter_template": [
        "cover letter", "covering letter", "letter of interest",
    ],
    # Work experience — filled from role-specific config
    "current_employer": [
        "current employer", "employer", "company", "company name", "employer name",
        "organization", "current company", "place of employment", "employer/company",
    ],
    "current_title": [
        "current title", "job title", "position", "title", "current position",
        "current role", "role", "position title", "your title",
    ],
    "employment_start": [
        "start date", "employment start", "start of employment", "from",
        "date started", "employment from",
    ],
    "employment_end": [
        "end date", "employment end", "end of employment", "to",
        "date ended", "employment to",
    ],
    "job_description": [
        "job description", "responsibilities", "duties", "role description",
        "describe your experience", "describe your work", "describe your role",
        "work description", "summary of experience", "experience description",
    ],
}

# Reverse index: pattern → profile_key (built once at module load)
_PATTERN_TO_KEY: dict[str, str] = {}
for _key, _patterns in FIELD_MAPPINGS.items():
    for _pattern in _patterns:
        _PATTERN_TO_KEY[_pattern] = _key


def _normalize(text: str) -> str:
    """Lowercase and strip punctuation/extra whitespace."""
    text = text.lower()
    text = re.sub(r"[*:()\[\]?]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _fuzzy_match(query: str, candidates: list[str]) -> tuple[Optional[str], float]:
    """
    Find the best fuzzy match for *query* among *candidates*.
    Returns (best_match, score) where score is 0..1.
    """
    best_candidate = None
    best_score = 0.0
    for candidate in candidates:
        score = SequenceMatcher(None, query, candidate).ratio()
        if score > best_score:
            best_score = score
            best_candidate = candidate
    return best_candidate, best_score


class FieldMapper:
    """Maps HTML form fields to profile data values."""

    def __init__(self, profile: dict, role_config: dict = None) -> None:
        self.profile = profile
        self.role_config = role_config or {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def map_field(self, field) -> tuple[Optional[str], float]:
        """
        Attempt to map a FormField to a profile value.

        Returns:
            (value, confidence) where confidence is 0..1.
            If no mapping is found, returns (None, 0.0).
        """
        # Collect candidate label strings from the field
        label_candidates: list[str] = []
        if getattr(field, "label", None):
            label_candidates.append(_normalize(field.label))
        if getattr(field, "name", None):
            label_candidates.append(_normalize(field.name.replace("_", " ").replace("-", " ")))

        best_profile_key: Optional[str] = None
        best_confidence: float = 0.0

        for label_text in label_candidates:
            # 1. Exact match against known patterns
            if label_text in _PATTERN_TO_KEY:
                profile_key = _PATTERN_TO_KEY[label_text]
                value = self._get_profile_value(profile_key)
                if value is not None:
                    return value, 1.0

            # 2. Substring match
            for pattern, profile_key in _PATTERN_TO_KEY.items():
                if pattern in label_text or label_text in pattern:
                    value = self._get_profile_value(profile_key)
                    if value is not None:
                        confidence = 0.85
                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_profile_key = profile_key

            # 3. Fuzzy match
            all_patterns = list(_PATTERN_TO_KEY.keys())
            matched_pattern, score = _fuzzy_match(label_text, all_patterns)
            if score > best_confidence and matched_pattern is not None:
                best_confidence = score
                best_profile_key = _PATTERN_TO_KEY[matched_pattern]

        if best_profile_key is not None and best_confidence >= 0.5:
            value = self._get_profile_value(best_profile_key)
            if value is not None:
                return value, best_confidence

        return None, 0.0

    def _get_profile_value(self, key: str) -> Optional[str]:
        """
        Extract a value from the profile dict by logical key.
        Handles compound keys such as 'first_name' derived from 'name'.
        """
        profile = self.profile

        # cover_letter_template: role-specific takes priority over base profile
        if key == "cover_letter_template":
            rc_template = self.role_config.get("cover_letter_template")
            if rc_template:
                return str(rc_template)
            val = profile.get("cover_letter_template")
            return str(val) if val else None

        # Direct key lookup first
        if key in profile and profile[key] is not None:
            raw = profile[key]
            # Convert booleans to human-readable strings
            if isinstance(raw, bool):
                return "Yes" if raw else "No"
            return str(raw)

        # Derived values
        if key == "first_name":
            name: str = profile.get("name", "")
            parts = name.strip().split()
            return parts[0] if parts else None

        if key == "last_name":
            name = profile.get("name", "")
            parts = name.strip().split()
            return parts[-1] if len(parts) > 1 else None

        if key == "full_name":
            return profile.get("name") or None

        if key == "address":
            city = profile.get("city", "")
            state = profile.get("state", "")
            zip_code = profile.get("zip_code", "")
            parts = [p for p in [city, state, zip_code] if p]
            return ", ".join(parts) if parts else None

        if key == "work_authorized":
            val = profile.get("work_authorized")
            if val is None:
                return None
            return "Yes" if val else "No"

        if key == "sponsorship_needed":
            val = profile.get("sponsorship_needed")
            if val is None:
                return None
            return "Yes" if val else "No"

        if key == "us_citizen":
            val = profile.get("us_citizen")
            if val is None:
                return None
            return "Yes" if val else "No"

        if key == "willing_to_relocate":
            val = profile.get("willing_to_relocate")
            if val is None:
                return None
            return "Yes" if val else "No"

        # Role-specific work experience (uses most recent entry at index 0)
        if key in ("current_employer", "current_title", "employment_start", "employment_end", "job_description"):
            wx = self.role_config.get("work_experience", [])
            if wx:
                entry = wx[0] if isinstance(wx[0], dict) else {}
                field_map = {
                    "current_employer": "company",
                    "current_title": "title",
                    "employment_start": "start_date",
                    "employment_end": "end_date",
                    "job_description": "description",
                }
                val = entry.get(field_map[key], "")
                if key == "employment_end" and not val:
                    return "Present"
                return val or None
            return None

        return None
