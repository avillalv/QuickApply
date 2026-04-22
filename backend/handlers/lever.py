from handlers.base import ATSHandler, FormField
from utils.field_mapper import FieldMapper


class LeverHandler(ATSHandler):
    """Handler for Lever ATS (jobs.lever.co)."""

    async def detect_platform(self, url: str) -> str:
        return "Lever"

    async def navigate_to_apply(self, page) -> None:
        apply_selectors = [
            "a.postings-btn",
            "a:has-text('Apply for this job')",
            "a:has-text('Apply')",
            "button:has-text('Apply')",
            ".btn-primary",
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

        # Lever forms use ul.application-questions li.application-question
        question_items = await page.query_selector_all(
            "li.application-question, .application-field, .form-group"
        )

        for item in question_items:
            label_el = await item.query_selector("label, .label")
            label_text = ""
            if label_el:
                label_text = (await label_el.inner_text()).strip()

            inp = await item.query_selector("input:not([type='hidden']), textarea, select")
            if not inp:
                continue

            tag = await inp.evaluate("el => el.tagName.toLowerCase()")
            input_type = await inp.evaluate("el => el.type || 'text'")
            name = await inp.evaluate("el => el.name || el.id || ''")
            required = await inp.evaluate("el => el.required")

            field_type = "textarea" if tag == "textarea" else (
                "select" if tag == "select" else input_type
            )

            ff = FormField(
                name=name,
                label=label_text or name,
                field_type=field_type,
                required=required,
            )

            value, confidence = mapper.map_field(ff)
            if value and confidence >= 0.5:
                ff.value = value
                ff.filled = True
            else:
                ff.needs_review = True

            fields.append(ff)

        # Also catch top-level inputs not in question containers
        top_inputs = await page.query_selector_all(
            "input[name='name'], input[name='email'], input[name='phone'], "
            "input[name='org'], input[name='urls[LinkedIn]'], input[name='urls[GitHub]']"
        )
        found_names = {f.name for f in fields}

        for inp in top_inputs:
            name = await inp.evaluate("el => el.name || ''")
            if name in found_names:
                continue
            input_type = await inp.evaluate("el => el.type || 'text'")
            required = await inp.evaluate("el => el.required")

            ff = FormField(name=name, label=name, field_type=input_type, required=required)
            value, confidence = mapper.map_field(ff)
            if value and confidence >= 0.5:
                ff.value = value
                ff.filled = True
            else:
                ff.needs_review = True
            fields.append(ff)

        return fields

    async def fill_field(self, page, form_field: FormField, value: str) -> None:
        if not value or not form_field.name:
            return

        sel = f"[name='{form_field.name}']"
        await self.random_delay(150, 450)

        if form_field.field_type == "select":
            await self.handle_dropdown(page, sel, value)
        elif form_field.field_type in ("checkbox", "radio"):
            el = await page.query_selector(sel)
            if el and not await el.is_checked():
                await el.click()
        else:
            await self.human_type(page, sel, value)

    async def upload_resume(self, page, file_path: str) -> None:
        selectors = [
            "input[type='file'][name*='resume']",
            "input[type='file'][name='cards[resume]']",
            "input[type='file'][accept*='pdf']",
            "input[type='file']",
        ]
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    await el.set_input_files(file_path)
                    await self.random_delay(500, 1000)
                    return
            except Exception:
                continue

    async def next_page(self, page) -> bool:
        # Lever forms are single-page; clicking submit completes the application
        return False

    async def submit(self, page) -> bool:
        submit_selectors = [
            "button.template-btn-submit",
            "button[type='submit']",
            ".submit-app-btn",
            "button:has-text('Submit application')",
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
