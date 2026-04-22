from handlers.base import ATSHandler, FormField
from utils.field_mapper import FieldMapper


class GreenhouseHandler(ATSHandler):
    """Handler for Greenhouse ATS (boards.greenhouse.io / job-boards.greenhouse.io)."""

    async def detect_platform(self, url: str) -> str:
        return "Greenhouse"

    async def navigate_to_apply(self, page) -> None:
        apply_selectors = [
            "a[href*='apply']",
            "a:has-text('Apply')",
            "button:has-text('Apply')",
            "#apply_button",
            ".apply-button",
        ]
        for sel in apply_selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    await el.click()
                    await page.wait_for_load_state("domcontentloaded", timeout=15000)
                    return
            except Exception:
                continue

    async def get_form_fields(self, page) -> list[FormField]:
        fields = []
        mapper = FieldMapper(self.profile)

        inputs = await page.query_selector_all(
            "input:not([type='hidden']):not([type='submit']):not([type='file']), textarea, select"
        )

        for inp in inputs:
            tag = await inp.evaluate("el => el.tagName.toLowerCase()")
            input_type = await inp.evaluate("el => el.type || ''")
            name = await inp.evaluate("el => el.name || el.id || ''")
            placeholder = await inp.evaluate("el => el.placeholder || ''")
            required = await inp.evaluate("el => el.required")

            # Find associated label text
            label_text = await _get_label_text(page, inp)

            field_type = "textarea" if tag == "textarea" else (
                "select" if tag == "select" else input_type or "text"
            )

            ff = FormField(
                name=name,
                label=label_text or placeholder or name,
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

        return fields

    async def fill_field(self, page, form_field: FormField, value: str) -> None:
        if not value:
            return

        sel = _build_selector(form_field)
        if not sel:
            return

        await self.random_delay(200, 500)

        if form_field.field_type == "select":
            await self.handle_dropdown(page, sel, value)
        elif form_field.field_type in ("checkbox", "radio"):
            el = await page.query_selector(sel)
            if el:
                is_checked = await el.is_checked()
                if not is_checked:
                    await el.click()
        else:
            await self.human_type(page, sel, value)

    async def upload_resume(self, page, file_path: str) -> None:
        selectors = [
            "input[type='file'][name*='resume']",
            "input[type='file'][id*='resume']",
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
        next_selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "button:has-text('Submit')",
            "button:has-text('Next')",
            "#submit_app",
        ]
        for sel in next_selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    await page.wait_for_load_state("domcontentloaded", timeout=15000)
                    return False  # Greenhouse is typically single-page
            except Exception:
                continue
        return False

    async def submit(self, page) -> bool:
        submit_selectors = [
            "input[type='submit'][value*='Submit']",
            "button[type='submit']",
            "#submit_app",
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
            const parent = el.closest('label');
            if (parent) return parent.innerText.replace(el.value || '', '').trim();
            const prev = el.previousElementSibling;
            if (prev && prev.tagName === 'LABEL') return prev.innerText.trim();
            return '';
        }""",
        element,
    )


def _build_selector(form_field: FormField) -> str:
    if form_field.name:
        return f"[name='{form_field.name}']"
    return ""
