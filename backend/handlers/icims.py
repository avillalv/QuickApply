"""
iCIMS ATS handler.

iCIMS portals typically appear at *.icims.com/jobs/* or as embedded iframes.
The application form uses consistent ID patterns.
"""
import asyncio
from handlers.base import ATSHandler, FormField
from utils.field_mapper import FieldMapper

# Known iCIMS field id/name patterns → profile keys
ICIMS_FIELD_MAP: dict[str, str] = {
    "initialsFirstName": "first_name",
    "initialsLastName": "last_name",
    "initial_email": "email",
    "email": "email",
    "initialsEmail": "email",
    "initialsPhone": "phone",
    "phone": "phone",
    "addressCity": "city",
    "addressState": "state",
    "addressZip": "zip_code",
    "addressPostalCode": "zip_code",
    "linkedIn": "linkedin_url",
    "websiteUrl": "portfolio_url",
    "resumeText": "cover_letter_template",
    "coverLetter": "cover_letter_template",
}


class ICIMSHandler(ATSHandler):

    async def detect_platform(self, url: str) -> str:
        return "iCIMS"

    async def navigate_to_apply(self, page) -> None:
        selectors = [
            "a.iCIMS_Button[href*='apply']",
            "a:has-text('Apply Now')",
            "button:has-text('Apply Now')",
            "a:has-text('Apply for Job')",
            ".iCIMS_JobApplication a",
            "#applyButton",
            "a[href*='apply'][class*='btn']",
        ]
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    href = await el.get_attribute("href")
                    if href and href.startswith("http"):
                        await page.goto(href, timeout=20000, wait_until="domcontentloaded")
                    else:
                        await el.click()
                        await page.wait_for_load_state("domcontentloaded", timeout=20000)
                    await asyncio.sleep(1)
                    return
            except Exception:
                continue

    async def get_form_fields(self, page) -> list[FormField]:
        mapper = FieldMapper(self.profile)
        fields: list[FormField] = []
        filled_names: set[str] = set()

        # --- Step 1: Known iCIMS field IDs ---
        for field_id, profile_key in ICIMS_FIELD_MAP.items():
            for sel in [f"#{field_id}", f"[name='{field_id}']", f"input[id*='{field_id}']"]:
                try:
                    el = await page.query_selector(sel)
                    if not el or not await el.is_visible():
                        continue

                    tag = await el.evaluate("e => e.tagName.toLowerCase()")
                    itype = await el.evaluate("e => e.type || 'text'")
                    field_type = "textarea" if tag == "textarea" else ("select" if tag == "select" else itype)
                    value = self._profile_value(profile_key)

                    ff = FormField(
                        name=field_id, label=profile_key.replace("_", " ").title(),
                        field_type=field_type, value=value,
                        confidence=1.0 if value else 0.0,
                        selector=sel,
                    )
                    if value:
                        try:
                            if field_type in ("text", "email", "tel"):
                                await page.fill(sel, value)
                            elif field_type == "textarea":
                                await page.fill(sel, value)
                            elif field_type == "select":
                                await self.handle_select(page, sel, value)
                            ff.filled = True
                        except Exception:
                            ff.needs_review = True
                    else:
                        ff.needs_review = True

                    fields.append(ff)
                    filled_names.add(field_id)
                    break
                except Exception:
                    continue

        # --- Step 2: Generic scan of remaining inputs ---
        inputs = await page.query_selector_all(
            "input:not([type='hidden']):not([type='submit']):not([type='file']),"
            "textarea, select"
        )
        for el in inputs:
            try:
                if not await el.is_visible():
                    continue
                id_attr = await el.get_attribute("id") or ""
                name_attr = await el.get_attribute("name") or ""
                key = id_attr or name_attr
                if not key or key in filled_names:
                    continue

                tag = await el.evaluate("e => e.tagName.toLowerCase()")
                itype = await el.evaluate("e => e.type || 'text'")
                field_type = "select" if tag == "select" else ("textarea" if tag == "textarea" else itype)
                if field_type in ("submit", "button", "image", "reset"):
                    continue

                label = await self._get_label_for_element(page, el)
                required = bool(await el.get_attribute("required") or await el.get_attribute("aria-required"))
                options = await self._get_options_for_select(page, el) if field_type == "select" else []

                ff = FormField(
                    name=key, label=label or key.replace("_", " ").title(),
                    field_type=field_type, required=required, options=options,
                    selector=f"#{id_attr}" if id_attr else f"[name='{name_attr}']",
                )
                value, confidence = mapper.map_field(ff)
                ff.value = value
                ff.confidence = confidence

                if value and confidence >= 0.6:
                    try:
                        sel_str = ff.selector
                        if field_type == "select":
                            await self.handle_select(page, sel_str, value)
                        elif field_type in ("checkbox", "radio"):
                            await self.handle_radio_or_checkbox(page, key, value)
                        elif field_type == "date":
                            await self.handle_date_field(page, sel_str, value)
                        else:
                            await page.fill(sel_str, value)
                        ff.filled = True
                    except Exception:
                        ff.needs_review = True
                else:
                    ff.needs_review = required or bool(label)

                fields.append(ff)
                filled_names.add(key)
            except Exception:
                continue

        # --- Step 3: Work authorization radio buttons ---
        await self._handle_work_auth(page, fields, filled_names)

        return fields

    async def _handle_work_auth(self, page, fields: list[FormField], filled_names: set) -> None:
        work_auth = self.profile.get("work_authorized")
        sponsorship = self.profile.get("sponsorship_needed")
        patterns = [
            ("authorized", work_auth, "Yes"),
            ("eligible", work_auth, "Yes"),
            ("sponsor", sponsorship, None),
        ]
        for pattern, profile_val, default in patterns:
            if profile_val is None and default is None:
                continue
            answer = "Yes" if profile_val else "No"
            try:
                radios = await page.query_selector_all("input[type='radio']")
                for radio in radios:
                    name = (await radio.get_attribute("name") or "").lower()
                    val = (await radio.get_attribute("value") or "").lower()
                    label_text = await self._get_label_for_element(page, radio)
                    if pattern in name or pattern in label_text.lower():
                        if answer.lower() in val:
                            await radio.click()
                            filled_names.add(name)
                            fields.append(FormField(
                                name=name, label=label_text, field_type="radio",
                                value=answer, filled=True, confidence=0.9,
                            ))
                            break
            except Exception:
                pass

    async def fill_field(self, page, form_field: FormField, value: str) -> None:
        if not value or not form_field.selector:
            return
        try:
            if form_field.field_type == "select":
                await self.handle_select(page, form_field.selector, value)
            elif form_field.field_type in ("checkbox", "radio"):
                await self.handle_radio_or_checkbox(page, form_field.name, value)
            elif form_field.field_type == "date":
                await self.handle_date_field(page, form_field.selector, value)
            else:
                await page.fill(form_field.selector, value)
        except Exception:
            pass

    async def upload_resume(self, page, file_path: str) -> None:
        selectors = [
            "input[type='file'][name*='resume']",
            "input[type='file'][id*='resume']",
            "input[type='file'][accept*='pdf']",
            ".iCIMS_FileUpload input[type='file']",
            "input[type='file']",
        ]
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    await el.set_input_files(file_path)
                    await asyncio.sleep(2)  # iCIMS processes uploads slowly
                    return
            except Exception:
                continue

    async def next_page(self, page) -> bool:
        selectors = [
            "button:has-text('Next')",
            "input[type='submit'][value='Next']",
            "a.iCIMS_Button:has-text('Next')",
            "button:has-text('Continue')",
            "button:has-text('Save & Continue')",
            "#iCIMS_Buttons_Continue",
            "[id*='btnNext']",
        ]
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    await page.wait_for_load_state("domcontentloaded", timeout=20000)
                    await asyncio.sleep(1)
                    return True
            except Exception:
                continue
        return False

    async def submit(self, page) -> bool:
        selectors = [
            "button:has-text('Submit')",
            "input[type='submit'][value*='Submit']",
            "#iCIMS_Buttons_Submit",
            "button[type='submit']",
            "[id*='btnSubmit']",
        ]
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    await page.wait_for_load_state("networkidle", timeout=25000)
                    return True
            except Exception:
                continue
        return False
