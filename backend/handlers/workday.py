"""
Workday ATS handler.

Workday forms use data-automation-id attributes extensively.
Forms are multi-step with dynamic loading between pages.
Typical steps: My Information → My Experience → Application Questions → Voluntary Disclosures
"""
import asyncio
import re
from typing import Optional

from handlers.base import ATSHandler, FormField
from utils.field_mapper import FieldMapper


# ---------------------------------------------------------------------------
# Known Workday field automation-id → profile key
# ---------------------------------------------------------------------------
WORKDAY_FIELD_MAP: dict[str, str] = {
    # Contact info
    "legalNameSection_firstName": "first_name",
    "legalNameSection_lastName": "last_name",
    "firstName": "first_name",
    "lastName": "last_name",
    "email": "email",
    "phone": "phone",
    "phoneNumber": "phone",
    "phoneDevice": "phone",
    # Address
    "city": "city",
    "state": "state",
    "postalCode": "zip_code",
    "zipCode": "zip_code",
    "country": None,  # Will default to "United States"
    # Work auth
    "workAuthorizationLegalRight": "work_authorized",
    "sponsorRequired": "sponsorship_needed",
    "requireSponsorship": "sponsorship_needed",
    # EEO / demographics
    "gender": "gender",
    "race": "race_ethnicity",
    "ethnicGroup": "race_ethnicity",
    "veteranStatus": "veteran_status",
    "disabilityStatus": "disability_status",
    # Social
    "linkedIn": "linkedin_url",
    "gitHub": "github_url",
    "website": "portfolio_url",
    # Salary / dates
    "desiredSalary": "salary_expectation",
    "availableStartDate": "start_date",
}

# EEO decline-to-answer values used on voluntary disclosure pages
EEO_DECLINE = "Decline to Self Identify"

YES_OPTIONS = {"yes", "y", "true", "1", "i am", "i do", "authorized", "eligible"}
NO_OPTIONS = {"no", "n", "false", "0", "i am not", "i do not", "not authorized"}


class WorkdayHandler(ATSHandler):

    async def detect_platform(self, url: str) -> str:
        return "Workday"

    async def navigate_to_apply(self, page) -> None:
        """Click the Apply button and wait for the application to load."""
        selectors = [
            '[data-automation-id="jobApplyButton"]',
            '[data-automation-id="applyButton"]',
            'a[href*="apply"][class*="css"]',
            'button:has-text("Apply")',
            'a:has-text("Apply Now")',
            'a:has-text("Apply for Job")',
        ]
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    await page.wait_for_load_state("networkidle", timeout=8000)
                    return
            except Exception:
                continue

    async def get_form_fields(self, page) -> list[FormField]:
        """
        Scan the current Workday page, map profile data, fill auto-mapped fields.
        Returns list of FormField with filled/needs_review set.
        """
        mapper = FieldMapper(self.profile)
        fields: list[FormField] = []
        filled_names: set[str] = set()

        # --- Step 1: Try known Workday field IDs ---
        for auto_id, profile_key in WORKDAY_FIELD_MAP.items():
            selectors_to_try = [
                f'[data-automation-id="{auto_id}"] input',
                f'[data-automation-id="{auto_id}"] textarea',
                f'[data-automation-id="{auto_id}"] select',
                f'input[data-automation-id="{auto_id}"]',
                f'select[data-automation-id="{auto_id}"]',
            ]
            el = None
            used_sel = None
            for sel in selectors_to_try:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        used_sel = sel
                        break
                except Exception:
                    pass

            if not el:
                continue

            tag = await el.evaluate("e => e.tagName.toLowerCase()")
            itype = await el.evaluate("e => e.type || 'text'")
            field_type = "select" if tag == "select" else ("textarea" if tag == "textarea" else itype)

            # Determine value
            if profile_key is None:
                # Country defaults to US
                ff = FormField(
                    name=auto_id, label="Country", field_type=field_type,
                    value="United States", filled=False, needs_review=False,
                    confidence=0.95, selector=used_sel,
                )
                await self._fill_workday_field(page, ff)
                fields.append(ff)
                filled_names.add(auto_id)
                continue

            value = self._profile_value(profile_key)
            ff = FormField(
                name=auto_id,
                label=profile_key.replace("_", " ").title(),
                field_type=field_type,
                value=value,
                confidence=1.0 if value else 0.0,
                selector=used_sel,
            )
            if value:
                await self._fill_workday_field(page, ff)
                ff.filled = True
            else:
                ff.needs_review = True
            fields.append(ff)
            filled_names.add(auto_id)

        # --- Step 2: Scan remaining inputs generically ---
        all_inputs = await page.query_selector_all(
            "input:not([type='hidden']):not([type='submit']):not([type='file']),"
            "textarea, select"
        )
        for el in all_inputs:
            try:
                auto_id = await el.get_attribute("data-automation-id") or ""
                name_attr = await el.get_attribute("name") or ""
                id_attr = await el.get_attribute("id") or ""
                field_key = auto_id or name_attr or id_attr

                if not field_key or field_key in filled_names:
                    continue

                visible = await el.is_visible()
                if not visible:
                    continue

                tag = await el.evaluate("e => e.tagName.toLowerCase()")
                itype = await el.evaluate("e => e.type || 'text'")
                field_type = "select" if tag == "select" else ("textarea" if tag == "textarea" else itype)
                label = await self._get_label_for_element(page, el)
                required = bool(
                    await el.get_attribute("aria-required") or
                    await el.get_attribute("required")
                )

                ff = FormField(
                    name=field_key, label=label or field_key,
                    field_type=field_type, required=required,
                    selector=f'[data-automation-id="{auto_id}"]' if auto_id else f'[name="{name_attr}"]' if name_attr else f'#{id_attr}',
                )

                value, confidence = mapper.map_field(ff)
                ff.value = value
                ff.confidence = confidence

                if value and confidence >= 0.65:
                    await self._fill_workday_field(page, ff)
                    ff.filled = True
                else:
                    ff.needs_review = required or bool(label)

                fields.append(ff)
                filled_names.add(field_key)
            except Exception:
                continue

        # --- Step 3: Handle radio/select groups for yes/no questions ---
        await self._handle_boolean_fields(page, fields, filled_names)

        # --- Step 4: Handle EEO voluntary disclosure section ---
        await self._handle_eeo_section(page, fields)

        return fields

    async def _fill_workday_field(self, page, ff: FormField) -> None:
        """Fill a single Workday field in the browser."""
        if not ff.value or not ff.selector:
            return
        try:
            el = await page.query_selector(ff.selector)
            if not el or not await el.is_visible():
                return

            tag = await el.evaluate("e => e.tagName.toLowerCase()")
            itype = await el.evaluate("e => (e.type || '').toLowerCase()")

            if tag == "select":
                await self.handle_select(page, ff.selector, ff.value)
            elif itype == "checkbox":
                checked = await el.is_checked()
                if ff.value.lower() in YES_OPTIONS and not checked:
                    await el.click()
                elif ff.value.lower() in NO_OPTIONS and checked:
                    await el.click()
            elif itype == "radio":
                await self.handle_radio_or_checkbox(page, ff.name, ff.value)
            else:
                # Workday text inputs — use fill() for speed, human_type if slow mode
                await el.click()
                await el.fill(ff.value)
            await asyncio.sleep(0.1)
        except Exception:
            pass

    async def fill_field(self, page, form_field: FormField, value: str) -> None:
        """Fill a field (used for user overrides from co-pilot)."""
        form_field.value = value
        if form_field.selector:
            await self._fill_workday_field(page, form_field)
        else:
            # Build selector on the fly
            if form_field.name:
                for sel in [
                    f'[data-automation-id="{form_field.name}"] input',
                    f'input[name="{form_field.name}"]',
                    f'#{form_field.name}',
                ]:
                    try:
                        el = await page.query_selector(sel)
                        if el and await el.is_visible():
                            await el.fill(value)
                            return
                    except Exception:
                        pass

    async def _handle_boolean_fields(self, page, fields: list[FormField], filled_names: set) -> None:
        """Handle yes/no radio groups for work authorization etc."""
        bool_patterns = [
            ("authorized", "work_authorized", "Yes"),
            ("sponsor", "sponsorship_needed", "No"),
            ("citizen", "us_citizen", "Yes"),
            ("relocat", "willing_to_relocate",
             "Yes" if self.profile.get("willing_to_relocate") else "No"),
        ]
        for pattern, profile_key, default_yes in bool_patterns:
            profile_val = self.profile.get(profile_key)
            if profile_val is None:
                continue
            answer = "Yes" if profile_val else "No"
            try:
                # Find radio groups matching the pattern
                radios = await page.query_selector_all(f"input[type='radio']")
                for radio in radios:
                    name = (await radio.get_attribute("name") or "").lower()
                    label_text = await self._get_label_for_element(page, radio)
                    if pattern in name or pattern in label_text.lower():
                        if answer.lower() in (await radio.get_attribute("value") or "").lower():
                            await radio.click()
                            filled_names.add(name)
                            fields.append(FormField(
                                name=name, label=label_text, field_type="radio",
                                value=answer, filled=True, confidence=0.95,
                            ))
                            break
            except Exception:
                pass

    async def _handle_eeo_section(self, page, fields: list[FormField]) -> None:
        """Pre-fill EEO/voluntary disclosure dropdowns from profile demographics."""
        eeo_map = {
            "gender": "gender",
            "race": "race_ethnicity",
            "ethnicity": "race_ethnicity",
            "veteran": "veteran_status",
            "disability": "disability_status",
        }
        for label_fragment, profile_key in eeo_map.items():
            profile_val = self.profile.get(profile_key)
            value = profile_val or EEO_DECLINE
            try:
                selects = await page.query_selector_all("select")
                for sel_el in selects:
                    name = (await sel_el.get_attribute("name") or "").lower()
                    label = await self._get_label_for_element(page, sel_el)
                    if label_fragment in name or label_fragment in label.lower():
                        sel_str = f"select[name='{await sel_el.get_attribute('name')}']"
                        if not await self.handle_select(page, sel_str, value):
                            # try to pick any available option with the value
                            opts = await sel_el.evaluate(
                                "e => Array.from(e.options).map(o => o.text)"
                            )
                            matching = next(
                                (o for o in opts if value.lower() in o.lower()), None
                            )
                            if matching:
                                await self.handle_select(page, sel_str, matching)
                        fields.append(FormField(
                            name=name or label_fragment, label=label or label_fragment,
                            field_type="select", value=value, filled=True, confidence=0.9,
                        ))
            except Exception:
                pass

    async def upload_resume(self, page, file_path: str) -> None:
        # Try "Autofill with Resume" button first (parses resume → pre-fills fields)
        autofill_selectors = [
            '[data-automation-id="autofillWithResume"]',
            'button:has-text("Autofill with Resume")',
            'button:has-text("Upload a Resume")',
            'button:has-text("Drop Your Resume")',
        ]
        for sel in autofill_selectors:
            try:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(0.4)
                    break
            except Exception:
                pass

        # Upload the actual file
        file_selectors = [
            'input[type="file"]',
            '[data-automation-id*="resume"] input[type="file"]',
            '[data-automation-id*="file"] input[type="file"]',
        ]
        for sel in file_selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    await el.set_input_files(file_path)
                    # Wait for upload processing
                    await page.wait_for_load_state("networkidle", timeout=8000)
                    await asyncio.sleep(0.4)
                    return
            except Exception:
                continue

    async def next_page(self, page) -> bool:
        """Click Workday's Next button. Returns True if more pages exist."""
        next_selectors = [
            '[data-automation-id="bottom-navigation-next-button"]',
            '[data-automation-id="nextButton"]',
            'button:has-text("Next")',
            'button:has-text("Save and Continue")',
            'button:has-text("Continue")',
        ]
        for sel in next_selectors:
            try:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click()
                    await page.wait_for_load_state("networkidle", timeout=8000)
                    await asyncio.sleep(0.3)
                    return True
            except Exception:
                continue
        return False

    async def submit(self, page) -> bool:
        submit_selectors = [
            '[data-automation-id="bottom-navigation-next-button"]',
            '[data-automation-id="submitButton"]',
            'button:has-text("Submit")',
            'button[type="submit"]',
        ]
        for sel in submit_selectors:
            try:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click()
                    await page.wait_for_load_state("networkidle", timeout=8000)
                    return True
            except Exception:
                continue
        return False
