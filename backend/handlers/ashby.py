"""
Ashby ATS handler (jobs.ashbyhq.com).

Ashby forms are React-based with data-testid attributes.
Multi-step wizard with sections: Basic Info, Questions, Resume.
"""
import asyncio
from handlers.base import ATSHandler, FormField
from utils.field_mapper import FieldMapper

ASHBY_FIELD_MAP: dict[str, str] = {
    "firstName": "first_name",
    "lastName": "last_name",
    "email": "email",
    "phoneNumber": "phone",
    "phone": "phone",
    "linkedInUrl": "linkedin_url",
    "githubUrl": "github_url",
    "portfolioUrl": "portfolio_url",
    "websiteUrl": "portfolio_url",
    "city": "city",
    "location": "city",
    "resumeInput": None,  # handled separately
}


class AshbyHandler(ATSHandler):

    async def detect_platform(self, url: str) -> str:
        return "Ashby"

    async def navigate_to_apply(self, page) -> None:
        selectors = [
            "a:has-text('Apply')",
            "button:has-text('Apply')",
            "[data-testid='apply-button']",
            "a[href*='apply']",
            ".ashby-job-posting-apply-button",
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
                        await page.wait_for_load_state("domcontentloaded", timeout=12000)
                    await asyncio.sleep(0.4)
                    return
            except Exception:
                continue

    async def get_form_fields(self, page) -> list[FormField]:
        mapper = FieldMapper(self.profile)
        fields: list[FormField] = []
        filled_names: set[str] = set()

        # --- Step 1: Known Ashby fields ---
        for field_name, profile_key in ASHBY_FIELD_MAP.items():
            if profile_key is None:
                continue
            selectors_to_try = [
                f"input[name='{field_name}']",
                f"[data-testid='{field_name}'] input",
                f"#{field_name}",
                f"input[placeholder*='{field_name.lower()}']",
            ]
            for sel in selectors_to_try:
                try:
                    el = await page.query_selector(sel)
                    if not el or not await el.is_visible():
                        continue

                    itype = await el.evaluate("e => e.type || 'text'")
                    value = self._profile_value(profile_key)

                    ff = FormField(
                        name=field_name,
                        label=profile_key.replace("_", " ").title(),
                        field_type=itype,
                        value=value,
                        confidence=1.0 if value else 0.0,
                        selector=sel,
                    )
                    if value:
                        try:
                            await page.fill(sel, value)
                            ff.filled = True
                        except Exception:
                            ff.needs_review = True
                    else:
                        ff.needs_review = True

                    fields.append(ff)
                    filled_names.add(field_name)
                    break
                except Exception:
                    continue

        # --- Step 2: Ashby custom question containers ---
        question_containers = await page.query_selector_all(
            "[data-testid*='question'], .ashby-application-form-question, "
            "[class*='FormQuestion'], [class*='applicationQuestion']"
        )
        for container in question_containers:
            try:
                label_el = await container.query_selector("label, legend, [class*='label'], p")
                label = (await label_el.inner_text()).strip() if label_el else ""

                inp = await container.query_selector(
                    "input:not([type='hidden']):not([type='submit']):not([type='file']), textarea, select"
                )
                if not inp:
                    # Check for radio/checkbox groups
                    radios = await container.query_selector_all("input[type='radio'], input[type='checkbox']")
                    if radios and label:
                        name = await radios[0].get_attribute("name") or label
                        if name not in filled_names:
                            ff = FormField(
                                name=name, label=label, field_type="radio",
                                needs_review=True, confidence=0.0,
                            )
                            # Try to auto-answer common questions
                            value, confidence = mapper.map_field(ff)
                            if value and confidence >= 0.7:
                                await self.handle_radio_or_checkbox(page, name, value)
                                ff.value = value
                                ff.filled = True
                                ff.confidence = confidence
                                ff.needs_review = False
                            fields.append(ff)
                            filled_names.add(name)
                    continue

                name = await inp.get_attribute("name") or await inp.get_attribute("id") or label
                if not name or name in filled_names:
                    continue
                if not await inp.is_visible():
                    continue

                tag = await inp.evaluate("e => e.tagName.toLowerCase()")
                itype = await inp.evaluate("e => e.type || 'text'")
                field_type = "select" if tag == "select" else ("textarea" if tag == "textarea" else itype)
                required = bool(await inp.get_attribute("required") or await inp.get_attribute("aria-required"))
                options = await self._get_options_for_select(page, inp) if field_type == "select" else []

                ff = FormField(
                    name=name, label=label or name,
                    field_type=field_type, required=required, options=options,
                    selector=f"[name='{name}']",
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
                        elif field_type == "textarea":
                            await page.fill(ff.selector, value)
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

        # --- Step 3: Generic scan for remaining fields ---
        inputs = await page.query_selector_all(
            "input:not([type='hidden']):not([type='submit']):not([type='file']),"
            "textarea, select"
        )
        for el in inputs:
            try:
                if not await el.is_visible():
                    continue
                name = await el.get_attribute("name") or await el.get_attribute("id") or ""
                if not name or name in filled_names:
                    continue

                tag = await el.evaluate("e => e.tagName.toLowerCase()")
                itype = await el.evaluate("e => e.type || 'text'")
                field_type = "select" if tag == "select" else ("textarea" if tag == "textarea" else itype)
                if field_type in ("submit", "button", "image"):
                    continue

                label = await self._get_label_for_element(page, el)
                required = bool(await el.get_attribute("required"))

                ff = FormField(
                    name=name, label=label or name.replace("_", " ").title(),
                    field_type=field_type, required=required,
                    selector=f"[name='{name}']" if await el.get_attribute("name") else f"#{name}",
                )
                value, confidence = mapper.map_field(ff)
                ff.value = value
                ff.confidence = confidence

                if value and confidence >= 0.65:
                    try:
                        if field_type == "select":
                            await self.handle_select(page, ff.selector, value)
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
            elif form_field.field_type == "textarea":
                # Ashby uses Quill or similar for long-form text
                success = await self.handle_rich_text(page, sel, value)
                if not success:
                    await page.fill(sel, value)
            else:
                await page.fill(sel, value)
        except Exception:
            pass

    async def upload_resume(self, page, file_path: str) -> None:
        selectors = [
            "input[type='file'][name*='resume']",
            "input[type='file'][data-testid*='resume']",
            "input[type='file'][accept*='pdf']",
            "input[type='file']",
        ]
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    await el.set_input_files(file_path)
                    await asyncio.sleep(0.6)
                    return
            except Exception:
                continue

    async def next_page(self, page) -> bool:
        selectors = [
            "button:has-text('Next')",
            "button:has-text('Continue')",
            "[data-testid='next-button']",
            "[data-testid='continue-button']",
            "button[type='button']:has-text('Next')",
        ]
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    await page.wait_for_load_state("networkidle", timeout=8000)
                    await asyncio.sleep(0.3)
                    return True
            except Exception:
                continue
        return False

    async def submit(self, page) -> bool:
        selectors = [
            "button:has-text('Submit')",
            "button:has-text('Submit Application')",
            "[data-testid='submit-button']",
            "button[type='submit']",
        ]
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    await page.wait_for_load_state("networkidle", timeout=8000)
                    return True
            except Exception:
                continue
        return False
