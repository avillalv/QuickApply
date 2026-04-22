"""
GenericHandler — fallback ATS handler using fuzzy field-label matching.
Used when no specific platform handler is matched.
"""
import difflib
from handlers.base import ATSHandler, FormField
from utils.field_mapper import FieldMapper

# Maps common label fragments → profile keys
_LABEL_TO_PROFILE = {
    "first name": "first_name",
    "last name": "last_name",
    "full name": "full_name",
    "name": "full_name",
    "email": "email",
    "phone": "phone",
    "mobile": "phone",
    "telephone": "phone",
    "linkedin": "linkedin_url",
    "github": "github_url",
    "portfolio": "portfolio_url",
    "website": "portfolio_url",
    "city": "city",
    "state": "state",
    "zip": "zip_code",
    "postal": "zip_code",
    "address": "city",
    "location": "city",
    "authorized": "work_authorized",
    "work authorization": "work_authorized",
    "sponsorship": "sponsorship_needed",
    "visa": "sponsorship_needed",
    "salary": "salary_expectation",
    "compensation": "salary_expectation",
    "expected salary": "salary_expectation",
    "start date": "start_date",
    "earliest start": "start_date",
    "relocate": "willing_to_relocate",
    "relocation": "willing_to_relocate",
    "school": "school",
    "university": "school",
    "college": "school",
    "degree": "degree",
    "major": "major",
    "gpa": "gpa",
    "graduation": "graduation_date",
    "graduate date": "graduation_date",
    "cover letter": "cover_letter_template",
    "how did you hear": "how_did_you_hear",
    "referral": "how_did_you_hear",
}


def _fuzzy_match_label(label: str) -> tuple[str | None, float]:
    """Return (profile_key, confidence) for the best matching label."""
    label_lower = label.lower().strip()

    # Exact substring match first
    for fragment, key in _LABEL_TO_PROFILE.items():
        if fragment in label_lower:
            return key, 0.9

    # Fuzzy match using difflib
    candidates = list(_LABEL_TO_PROFILE.keys())
    matches = difflib.get_close_matches(label_lower, candidates, n=1, cutoff=0.5)
    if matches:
        key = _LABEL_TO_PROFILE[matches[0]]
        score = difflib.SequenceMatcher(None, label_lower, matches[0]).ratio()
        return key, score

    return None, 0.0


class GenericHandler(ATSHandler):
    """
    Fallback handler that attempts to fill any ATS form using fuzzy label matching.
    Marks fields with confidence < 0.6 as needing review.
    """

    async def detect_platform(self, url: str) -> str:
        return "Custom ATS"

    async def navigate_to_apply(self, page) -> None:
        apply_selectors = [
            "a:has-text('Apply')", "button:has-text('Apply')",
            "a:has-text('Apply Now')", "button:has-text('Apply Now')",
            "a[href*='apply']", "a[class*='apply']", "button[class*='apply']",
        ]
        for sel in apply_selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    await page.wait_for_load_state("domcontentloaded", timeout=15000)
                    return
            except Exception:
                continue

    async def get_form_fields(self, page) -> list[FormField]:
        fields = []
        mapper = FieldMapper(self.profile)

        elements = await page.query_selector_all(
            "input:not([type='hidden']):not([type='submit']):not([type='button']), "
            "textarea, select"
        )

        seen_names: set[str] = set()

        for el in elements:
            tag = await el.evaluate("el => el.tagName.toLowerCase()")
            input_type = await el.evaluate("el => el.type || 'text'")
            name = await el.evaluate("el => el.name || el.id || ''")
            placeholder = await el.evaluate("el => el.placeholder || ''")
            aria_label = await el.evaluate("el => el.getAttribute('aria-label') || ''")
            required = await el.evaluate("el => el.required")

            if name in seen_names:
                continue
            if name:
                seen_names.add(name)

            # Find label text
            label_text = await _get_label_text(page, el)
            label = label_text or aria_label or placeholder or name

            field_type = "textarea" if tag == "textarea" else (
                "select" if tag == "select" else input_type or "text"
            )

            # Skip purely decorative/search inputs
            if field_type in ("search", "button", "image", "reset", "color", "range"):
                continue

            ff = FormField(
                name=name,
                label=label,
                field_type=field_type,
                required=required,
            )

            # Try FieldMapper first (uses profile key mappings)
            value, confidence = mapper.map_field(ff)

            # If low confidence, try fuzzy label matching
            if confidence < 0.6:
                profile_key, fuzz_conf = _fuzzy_match_label(label)
                if profile_key and fuzz_conf > confidence:
                    value = _get_profile_value(self.profile, profile_key)
                    confidence = fuzz_conf

            if value and confidence >= 0.6:
                ff.value = value
                ff.filled = True
                ff.needs_review = False
            else:
                ff.needs_review = True

            fields.append(ff)

        return fields

    async def fill_field(self, page, form_field: FormField, value: str) -> None:
        if not value:
            return

        sel = _build_selector(form_field)
        if not sel:
            return

        await self.random_delay(200, 600)

        try:
            if form_field.field_type == "select":
                await self.handle_dropdown(page, sel, value)
            elif form_field.field_type in ("checkbox", "radio"):
                el = await page.query_selector(sel)
                if el and not await el.is_checked():
                    await el.click()
            else:
                await self.human_type(page, sel, value)
        except Exception:
            pass

    async def upload_resume(self, page, file_path: str) -> None:
        file_inputs = await page.query_selector_all("input[type='file']")
        for inp in file_inputs:
            try:
                await inp.set_input_files(file_path)
                await self.random_delay(500, 1000)
                return
            except Exception:
                continue

    async def next_page(self, page) -> bool:
        next_selectors = [
            "button:has-text('Next')", "button:has-text('Continue')",
            "input[type='submit'][value*='Next']", "a:has-text('Next')",
            "[data-action='next']",
        ]
        for sel in next_selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    await page.wait_for_load_state("domcontentloaded", timeout=15000)
                    return True
            except Exception:
                continue
        return False

    async def submit(self, page) -> bool:
        submit_selectors = [
            "button[type='submit']", "input[type='submit']",
            "button:has-text('Submit')", "button:has-text('Apply')",
            "button:has-text('Submit Application')",
        ]
        for sel in submit_selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    await page.wait_for_load_state("domcontentloaded", timeout=20000)
                    return True
            except Exception:
                continue
        return False


async def _get_label_text(page, element) -> str:
    return await page.evaluate(
        """el => {
            const id = el.id;
            if (id) {
                const lbl = document.querySelector(`label[for="${id}"]`);
                if (lbl) return lbl.innerText.trim();
            }
            const parent = el.closest('.form-group, .field-wrapper, .form-field, li');
            if (parent) {
                const lbl = parent.querySelector('label, .label, .field-label');
                if (lbl) return lbl.innerText.trim();
            }
            const prev = el.previousElementSibling;
            if (prev && ['LABEL', 'SPAN', 'P'].includes(prev.tagName)) {
                return prev.innerText.trim();
            }
            return '';
        }""",
        element,
    )


def _build_selector(form_field: FormField) -> str:
    if form_field.name:
        return f"[name='{form_field.name}']"
    return ""


def _get_profile_value(profile: dict, key: str) -> str | None:
    value = profile.get(key)
    if value is None:
        return None
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value)
