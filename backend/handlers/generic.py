"""
GenericHandler — fuzzy label-matching fallback for unknown ATS platforms.
"""
import difflib
import asyncio
from handlers.base import ATSHandler, FormField
from utils.field_mapper import FieldMapper

_LABEL_FRAGMENTS: dict[str, str] = {
    "first name": "first_name", "first": "first_name",
    "last name": "last_name", "last": "last_name",
    "full name": "full_name", "name": "full_name",
    "email": "email", "e-mail": "email",
    "phone": "phone", "mobile": "phone", "telephone": "phone",
    "linkedin": "linkedin_url",
    "github": "github_url",
    "portfolio": "portfolio_url", "website": "portfolio_url",
    "city": "city", "location": "city",
    "state": "state", "province": "state",
    "zip": "zip_code", "postal": "zip_code",
    "authorized": "work_authorized",
    "sponsorship": "sponsorship_needed", "visa": "sponsorship_needed",
    "salary": "salary_expectation", "compensation": "salary_expectation",
    "start date": "start_date", "available": "start_date",
    "relocate": "willing_to_relocate",
    "school": "school", "university": "school", "college": "school",
    "degree": "degree", "education": "degree",
    "major": "major", "field of study": "major",
    "gpa": "gpa",
    "cover letter": "cover_letter_template",
    "gender": "gender",
    "race": "race_ethnicity", "ethnicity": "race_ethnicity",
    "veteran": "veteran_status",
    "disability": "disability_status",
}


def _fuzzy_label_match(label: str) -> tuple[str | None, float]:
    label_lower = label.lower().strip()
    for fragment, key in _LABEL_FRAGMENTS.items():
        if fragment in label_lower:
            return key, 0.9
    matches = difflib.get_close_matches(label_lower, list(_LABEL_FRAGMENTS.keys()), n=1, cutoff=0.55)
    if matches:
        key = _LABEL_FRAGMENTS[matches[0]]
        score = difflib.SequenceMatcher(None, label_lower, matches[0]).ratio()
        return key, score
    return None, 0.0


class GenericHandler(ATSHandler):

    async def detect_platform(self, url: str) -> str:
        return "Custom ATS"

    async def navigate_to_apply(self, page) -> None:
        selectors = [
            "a:has-text('Apply Now')", "button:has-text('Apply Now')",
            "a:has-text('Apply')", "button:has-text('Apply')",
            "a[class*='apply']", "button[class*='apply']",
            "a[href*='apply']",
        ]
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    await page.wait_for_load_state("domcontentloaded", timeout=10000)
                    return
            except Exception:
                continue

    async def get_form_fields(self, page) -> list[FormField]:
        mapper = FieldMapper(self.profile)
        fields: list[FormField] = []
        seen: set[str] = set()

        elements = await page.query_selector_all(
            "input:not([type='hidden']):not([type='submit']):not([type='button']):not([type='file']),"
            "textarea, select"
        )

        for el in elements:
            try:
                if not await el.is_visible():
                    continue

                tag = await el.evaluate("e => e.tagName.toLowerCase()")
                itype = await el.evaluate("e => e.type || 'text'")
                name = await el.evaluate("e => e.name || e.id || ''")
                placeholder = await el.evaluate("e => e.placeholder || ''")
                required = await el.evaluate("e => e.required")
                aria_label = await el.get_attribute("aria-label") or ""

                if name in seen or not name:
                    # Still include nameless elements by index
                    name = f"field_{len(fields)}"

                seen.add(name)

                field_type = "select" if tag == "select" else (
                    "textarea" if tag == "textarea" else itype or "text"
                )
                if field_type in ("submit", "button", "image", "reset", "search"):
                    continue

                label = await self._get_label_for_element(page, el)
                label_text = label or aria_label or placeholder or name

                ff = FormField(
                    name=name, label=label_text, field_type=field_type,
                    required=required,
                    selector=f"[name='{await el.evaluate('e => e.name')}']" if await el.evaluate("e => e.name") else None,
                )

                # Try FieldMapper first
                value, confidence = mapper.map_field(ff)

                # Fall back to fuzzy label match
                if confidence < 0.6:
                    profile_key, fuzz_conf = _fuzzy_label_match(label_text)
                    if profile_key and fuzz_conf > confidence:
                        value = mapper._get_profile_value(profile_key)
                        confidence = fuzz_conf

                ff.value = value
                ff.confidence = confidence

                if value and confidence >= 0.6:
                    try:
                        sel_str = ff.selector or f"[name='{name}']"
                        if field_type == "select":
                            await self.handle_select(page, sel_str, value)
                        elif field_type in ("checkbox", "radio"):
                            await self.handle_radio_or_checkbox(page, name, value)
                        else:
                            await page.fill(sel_str, value)
                        ff.filled = True
                    except Exception:
                        ff.needs_review = True
                else:
                    ff.needs_review = required or bool(label)

                fields.append(ff)
            except Exception:
                continue

        return fields

    async def fill_field(self, page, form_field: FormField, value: str) -> None:
        if not value:
            return
        try:
            sel = form_field.selector or f"[name='{form_field.name}']"
            if form_field.field_type == "select":
                await self.handle_select(page, sel, value)
            elif form_field.field_type in ("checkbox", "radio"):
                await self.handle_radio_or_checkbox(page, form_field.name, value)
            else:
                await page.fill(sel, value)
        except Exception:
            pass

    async def upload_resume(self, page, file_path: str) -> None:
        inputs = await page.query_selector_all("input[type='file']")
        for inp in inputs:
            try:
                await inp.set_input_files(file_path)
                await asyncio.sleep(0.3)
                return
            except Exception:
                continue

    async def next_page(self, page) -> bool:
        selectors = [
            "button:has-text('Next')", "button:has-text('Continue')",
            "input[type='submit'][value*='Next']",
            "a:has-text('Next')", "[data-action='next']",
            "button:has-text('Save and Continue')",
        ]
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    await page.wait_for_load_state("domcontentloaded", timeout=10000)
                    return True
            except Exception:
                continue
        return False

    async def submit(self, page) -> bool:
        selectors = [
            "button[type='submit']", "input[type='submit']",
            "button:has-text('Submit')", "button:has-text('Apply')",
            "button:has-text('Submit Application')",
        ]
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    await page.wait_for_load_state("domcontentloaded", timeout=12000)
                    return True
            except Exception:
                continue
        return False
