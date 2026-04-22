"""
Greenhouse ATS handler (boards.greenhouse.io / job-boards.greenhouse.io).
Greenhouse forms are mostly single-page with standard HTML inputs plus
a custom questions section at the bottom.
"""
import asyncio
from handlers.base import ATSHandler, FormField
from utils.field_mapper import FieldMapper

# Greenhouse uses consistent input name attributes
GREENHOUSE_NAME_MAP: dict[str, str] = {
    "first_name": "first_name",
    "last_name": "last_name",
    "email": "email",
    "phone": "phone",
    "job_application[answers_attributes][0][text_value]": None,  # cover letter
    "resume": None,  # resume upload
}

# Known name attribute patterns → profile keys
GH_FIELD_NAMES: dict[str, str] = {
    "first_name": "first_name",
    "last_name": "last_name",
    "email": "email",
    "phone": "phone",
    "location": "city",
    "resume_text": "cover_letter_template",
    "cover_letter": "cover_letter_template",
    "linkedin_profile_url": "linkedin_url",
    "website": "portfolio_url",
}


class GreenhouseHandler(ATSHandler):

    async def detect_platform(self, url: str) -> str:
        return "Greenhouse"

    async def navigate_to_apply(self, page) -> None:
        """Greenhouse posting pages have an Apply button; click it if present."""
        selectors = [
            "a.button--green",
            "a[href*='apply']:not([href*='already'])",
            "button:has-text('Apply')",
            "#apply_button",
            ".apply-button",
        ]
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    href = await el.get_attribute("href")
                    if href and href.startswith("http"):
                        await page.goto(href, timeout=15000, wait_until="domcontentloaded")
                    else:
                        await el.click()
                        await page.wait_for_load_state("domcontentloaded", timeout=15000)
                    return
            except Exception:
                continue
        # If already on the application form page, nothing to do
        url = page.url
        if "application" in url or "apply" in url:
            return

    async def get_form_fields(self, page) -> list[FormField]:
        mapper = FieldMapper(self.profile)
        fields: list[FormField] = []
        filled_names: set[str] = set()

        # --- Core Greenhouse fields by known name attributes ---
        for name_attr, profile_key in GH_FIELD_NAMES.items():
            el = await page.query_selector(f"input[name='{name_attr}'], textarea[name='{name_attr}']")
            if not el:
                continue
            try:
                visible = await el.is_visible()
                if not visible:
                    continue
            except Exception:
                continue

            tag = await el.evaluate("e => e.tagName.toLowerCase()")
            field_type = "textarea" if tag == "textarea" else "text"
            value = self._profile_value(profile_key) if profile_key else None
            required = bool(await el.get_attribute("required"))

            ff = FormField(
                name=name_attr, label=name_attr.replace("_", " ").title(),
                field_type=field_type, value=value, required=required,
                confidence=1.0 if value else 0.0,
                selector=f"[name='{name_attr}']",
            )
            if value:
                try:
                    await page.fill(f"[name='{name_attr}']", value)
                    ff.filled = True
                except Exception:
                    ff.needs_review = True
            else:
                ff.needs_review = required

            fields.append(ff)
            filled_names.add(name_attr)

        # --- Scan remaining inputs ---
        inputs = await page.query_selector_all(
            "input:not([type='hidden']):not([type='submit']):not([type='file']),"
            "textarea, select"
        )
        for el in inputs:
            try:
                name = await el.get_attribute("name") or ""
                id_attr = await el.get_attribute("id") or ""
                key = name or id_attr
                if not key or key in filled_names:
                    continue
                if not await el.is_visible():
                    continue

                tag = await el.evaluate("e => e.tagName.toLowerCase()")
                itype = await el.evaluate("e => e.type || 'text'")
                field_type = "select" if tag == "select" else ("textarea" if tag == "textarea" else itype)
                label = await self._get_label_for_element(page, el)
                required = bool(await el.get_attribute("required"))

                ff = FormField(
                    name=key, label=label or key.replace("_", " ").title(),
                    field_type=field_type, required=required,
                    selector=f"[name='{name}']" if name else f"#{id_attr}",
                )
                value, confidence = mapper.map_field(ff)
                ff.value = value
                ff.confidence = confidence

                if value and confidence >= 0.6:
                    try:
                        if field_type == "select":
                            await self.handle_select(page, ff.selector, value)
                        elif field_type in ("checkbox", "radio"):
                            await self.handle_radio_or_checkbox(page, name, value)
                        else:
                            await page.fill(ff.selector, value)
                        ff.filled = True
                    except Exception:
                        ff.needs_review = True
                else:
                    ff.needs_review = required or bool(label)

                fields.append(ff)
                filled_names.add(key)
            except Exception:
                continue

        # --- Handle custom question selects and checkboxes ---
        custom_questions = await page.query_selector_all(
            ".custom-question, [id^='question_']"
        )
        for q_el in custom_questions:
            try:
                label_el = await q_el.query_selector("label, .field-label, legend")
                label = (await label_el.inner_text()).strip() if label_el else "Question"
                inp = await q_el.query_selector("select, input, textarea")
                if not inp:
                    continue
                name = await inp.get_attribute("name") or label
                if name in filled_names:
                    continue
                tag = await inp.evaluate("e => e.tagName.toLowerCase()")
                itype = await inp.evaluate("e => e.type || 'text'")
                field_type = "select" if tag == "select" else ("textarea" if tag == "textarea" else itype)

                fields.append(FormField(
                    name=name, label=label, field_type=field_type,
                    needs_review=True, confidence=0.0,
                    selector=f"[name='{name}']",
                ))
                filled_names.add(name)
            except Exception:
                continue

        return fields

    async def fill_field(self, page, form_field: FormField, value: str) -> None:
        if not value or not form_field.selector:
            return
        try:
            if form_field.field_type == "select":
                await self.handle_select(page, form_field.selector, value)
            elif form_field.field_type in ("checkbox", "radio"):
                await self.handle_radio_or_checkbox(page, form_field.name, value)
            elif form_field.field_type == "textarea":
                await page.fill(form_field.selector, value)
            else:
                await page.fill(form_field.selector, value)
        except Exception:
            pass

    async def upload_resume(self, page, file_path: str) -> None:
        selectors = [
            "input[type='file'][name='resume']",
            "input[type='file'][id*='resume']",
            "input[type='file'][accept*='pdf']",
            "input[type='file']",
        ]
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    await el.set_input_files(file_path)
                    await asyncio.sleep(1)
                    return
            except Exception:
                continue

    async def next_page(self, page) -> bool:
        # Greenhouse is single-page — no "next" until submit
        return False

    async def submit(self, page) -> bool:
        submit_selectors = [
            "input[type='submit']",
            "button[type='submit']",
            "#submit_app",
            "button:has-text('Submit Application')",
            "button:has-text('Submit')",
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
