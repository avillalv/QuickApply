"""
Lever ATS handler (jobs.lever.co).
Lever forms are single-page with consistent field names.
"""
import asyncio
from handlers.base import ATSHandler, FormField
from utils.field_mapper import FieldMapper

# Lever uses these consistent name attributes
LEVER_FIELDS: dict[str, str] = {
    "name": "full_name",
    "email": "email",
    "phone": "phone",
    "org": "school",                  # "Current company / school"
    "location": "city",
    "urls[LinkedIn]": "linkedin_url",
    "urls[GitHub]": "github_url",
    "urls[Portfolio]": "portfolio_url",
    "urls[Other]": "portfolio_url",
}


class LeverHandler(ATSHandler):

    async def detect_platform(self, url: str) -> str:
        return "Lever"

    async def navigate_to_apply(self, page) -> None:
        selectors = [
            "a.postings-btn",
            "a:has-text('Apply for this job')",
            "a:has-text('Apply for Job')",
            "a:has-text('Apply')",
            ".apply-btn",
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
                        await page.wait_for_load_state("domcontentloaded", timeout=10000)
                    return
            except Exception:
                continue

    async def get_form_fields(self, page) -> list[FormField]:
        mapper = FieldMapper(self.profile)
        fields: list[FormField] = []
        filled_names: set[str] = set()

        # --- Known Lever fields ---
        for name_attr, profile_key in LEVER_FIELDS.items():
            el = await page.query_selector(
                f"input[name='{name_attr}'], textarea[name='{name_attr}']"
            )
            if not el:
                continue
            try:
                if not await el.is_visible():
                    continue
            except Exception:
                continue

            tag = await el.evaluate("e => e.tagName.toLowerCase()")
            field_type = "textarea" if tag == "textarea" else "text"
            value = self._profile_value(profile_key)
            required = bool(await el.get_attribute("required"))

            ff = FormField(
                name=name_attr,
                label=name_attr.replace("_", " ").replace("urls[", "").replace("]", "").title(),
                field_type=field_type,
                value=value,
                required=required,
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

        # --- Lever custom questions (li.application-question) ---
        question_items = await page.query_selector_all(
            "li.application-question, .application-field, .custom-question"
        )
        for item in question_items:
            try:
                label_el = await item.query_selector(
                    "label, .application-label, .field-label, legend"
                )
                label = (await label_el.inner_text()).strip() if label_el else ""

                inp = await item.query_selector(
                    "input:not([type='hidden']):not([type='file']), textarea, select"
                )
                if not inp:
                    continue

                name = await inp.get_attribute("name") or label
                if name in filled_names:
                    continue
                if not await inp.is_visible():
                    continue

                tag = await inp.evaluate("e => e.tagName.toLowerCase()")
                itype = await inp.evaluate("e => e.type || 'text'")
                field_type = "select" if tag == "select" else ("textarea" if tag == "textarea" else itype)
                required = bool(await inp.get_attribute("required"))

                ff = FormField(
                    name=name, label=label or name,
                    field_type=field_type, required=required,
                    selector=f"[name='{name}']" if name else None,
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
                filled_names.add(name)
            except Exception:
                continue

        # --- Cover letter textarea ---
        for sel in ["textarea[name='comments']", "textarea.cards-textarea", "textarea"]:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    name = await el.get_attribute("name") or "cover_letter"
                    if name not in filled_names:
                        value = self._profile_value("cover_letter_template")
                        ff = FormField(
                            name=name, label="Cover Letter", field_type="textarea",
                            value=value, confidence=0.9 if value else 0.0,
                            selector=sel,
                        )
                        if value:
                            await page.fill(sel, value)
                            ff.filled = True
                        else:
                            ff.needs_review = True
                        fields.append(ff)
                        filled_names.add(name)
                        break
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
        selectors = [
            "input[type='file'][name*='resume']",
            "input[type='file'][name='cards[resume]']",
            "input[type='file'][accept*='pdf']",
            ".resume-upload input[type='file']",
            "input[type='file']",
        ]
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    await el.set_input_files(file_path)
                    await asyncio.sleep(0.3)
                    return
            except Exception:
                continue

    async def next_page(self, page) -> bool:
        return False  # Lever is single-page

    async def submit(self, page) -> bool:
        selectors = [
            "button.template-btn-submit",
            ".submit-app-btn",
            "button[type='submit']",
            "button:has-text('Submit application')",
            "button:has-text('Submit')",
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
