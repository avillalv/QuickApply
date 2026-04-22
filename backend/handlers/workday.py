import re
from typing import Optional
from .base import ATSHandler, FormField


class WorkdayHandler(ATSHandler):
    """
    Handler for Workday ATS job applications.

    Workday uses data-automation-id attributes extensively and renders
    multi-step, dynamically-loaded forms.
    """

    PLATFORM_NAME = "Workday"

    # URL patterns that indicate a Workday-hosted posting
    URL_PATTERNS = [
        r"\.myworkdayjobs\.com",
        r"\.wd\d+\.myworkdaysite\.com",
        r"workday\.com/en-US/recruiting",
    ]

    # Selectors used across Workday forms
    APPLY_BUTTON_SELECTORS = [
        '[data-automation-id="jobApplyButton"]',
        '[data-automation-id="applyButton"]',
        'a[href*="apply"]',
        'button:has-text("Apply")',
        'a:has-text("Apply Now")',
    ]

    NEXT_BUTTON_SELECTORS = [
        '[data-automation-id="bottom-navigation-next-button"]',
        '[data-automation-id="nextButton"]',
        'button:has-text("Next")',
        'button:has-text("Continue")',
    ]

    SUBMIT_BUTTON_SELECTORS = [
        '[data-automation-id="bottom-navigation-next-button"]',
        '[data-automation-id="submitButton"]',
        'button:has-text("Submit")',
        'button[type="submit"]',
    ]

    # ------------------------------------------------------------------
    # ATSHandler interface
    # ------------------------------------------------------------------

    async def detect_platform(self, url: str) -> str:
        for pattern in self.URL_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return self.PLATFORM_NAME
        return "Unknown"

    async def navigate_to_apply(self, page) -> None:
        """Click the Apply button and wait for the form to load."""
        for selector in self.APPLY_BUTTON_SELECTORS:
            try:
                button = await page.query_selector(selector)
                if button:
                    await button.click()
                    await page.wait_for_load_state("networkidle", timeout=30000)
                    return
            except Exception:
                continue
        raise RuntimeError("Could not find the Apply button on the Workday job page.")

    async def get_form_fields(self, page) -> list[FormField]:
        """
        Scan the current Workday form page for fillable fields.
        Workday wraps inputs in elements with data-automation-id.
        """
        fields: list[FormField] = []

        # Query all input/textarea/select elements
        elements = await page.query_selector_all(
            "input:not([type='hidden']):not([type='file']):not([type='submit']), "
            "textarea, "
            "select"
        )

        for element in elements:
            tag = await element.evaluate("el => el.tagName.toLowerCase()")
            input_type = await element.get_attribute("type") or "text"
            name_attr = await element.get_attribute("name") or ""
            id_attr = await element.get_attribute("id") or ""
            automation_id = await element.get_attribute("data-automation-id") or ""
            placeholder = await element.get_attribute("placeholder") or ""
            aria_label = await element.get_attribute("aria-label") or ""
            required = await element.get_attribute("aria-required") or await element.get_attribute("required") or ""

            # Resolve the label text
            label_text = await self._resolve_label(page, element, id_attr, automation_id, aria_label, placeholder)

            if tag == "select":
                field_type = "select"
                options = await element.evaluate(
                    "el => Array.from(el.options).map(o => o.text.trim())"
                )
            elif tag == "textarea":
                field_type = "textarea"
                options = []
            elif input_type in ("checkbox",):
                field_type = "checkbox"
                options = []
            elif input_type in ("radio",):
                field_type = "radio"
                options = []
            else:
                field_type = "text"
                options = []

            field_name = name_attr or id_attr or automation_id or label_text.lower().replace(" ", "_")

            form_field = FormField(
                name=field_name,
                label=label_text,
                field_type=field_type,
                options=options if options else [],
                required=bool(required and required not in ("false", "0")),
            )
            fields.append(form_field)

        # Also detect file upload inputs separately
        file_inputs = await page.query_selector_all("input[type='file']")
        for el in file_inputs:
            automation_id = await el.get_attribute("data-automation-id") or ""
            fields.append(
                FormField(
                    name=automation_id or "resume_upload",
                    label="Resume Upload",
                    field_type="file",
                )
            )

        return fields

    async def fill_field(self, page, form_field: FormField, value: str) -> None:
        """Fill a form field identified by its name/automation-id."""
        selector = self._build_selector(form_field)

        if form_field.field_type == "select":
            await self.handle_dropdown(page, selector, value)
        elif form_field.field_type in ("checkbox", "radio"):
            # Check if value is truthy
            if value.lower() in ("yes", "true", "1"):
                el = await page.query_selector(selector)
                if el:
                    is_checked = await el.is_checked()
                    if not is_checked:
                        await el.click()
        else:
            await self.human_type(page, selector, value)

        form_field.filled = True
        await self.random_delay(100, 300)

    async def upload_resume(self, page, file_path: str) -> None:
        """
        Find the resume file input and upload the PDF.
        Tries to use the Workday "Autofill with Resume" button first.
        """
        # Check for "Autofill with resume" / "Resume upload" button
        autofill_selectors = [
            '[data-automation-id="autofillWithResume"]',
            'button:has-text("Autofill with Resume")',
            'button:has-text("Upload Resume")',
            '[data-automation-id="resume-upload-button"]',
        ]
        for sel in autofill_selectors:
            try:
                btn = await page.query_selector(sel)
                if btn:
                    await btn.click()
                    await self.random_delay(500, 1000)
                    break
            except Exception:
                continue

        # Find the actual file input and set the file
        file_input_selectors = [
            'input[type="file"]',
            '[data-automation-id*="resume"] input[type="file"]',
            '[data-automation-id*="file"] input[type="file"]',
        ]
        for sel in file_input_selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    await el.set_input_files(file_path)
                    await page.wait_for_load_state("networkidle", timeout=15000)
                    return
            except Exception:
                continue

        raise RuntimeError("Could not find a resume file input on the Workday form.")

    async def next_page(self, page) -> bool:
        """
        Click the Next button to advance the multi-step form.
        Returns False if no Next button is found (may be the last page).
        """
        for selector in self.NEXT_BUTTON_SELECTORS:
            try:
                btn = await page.query_selector(selector)
                if btn and await btn.is_visible():
                    await btn.click()
                    await page.wait_for_load_state("networkidle", timeout=30000)
                    await self.random_delay(500, 1200)
                    return True
            except Exception:
                continue
        return False

    async def submit(self, page) -> bool:
        """Click the Submit button to complete the application."""
        for selector in self.SUBMIT_BUTTON_SELECTORS:
            try:
                btn = await page.query_selector(selector)
                if btn and await btn.is_visible():
                    await btn.click()
                    await page.wait_for_load_state("networkidle", timeout=30000)
                    return True
            except Exception:
                continue
        return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_selector(self, form_field: FormField) -> str:
        """Build a CSS selector for the given FormField."""
        if form_field.name:
            # Try data-automation-id first (Workday's primary identifier)
            return (
                f'[data-automation-id="{form_field.name}"], '
                f'[name="{form_field.name}"], '
                f'#{form_field.name}'
            )
        return f'[aria-label="{form_field.label}"]'

    async def _resolve_label(
        self,
        page,
        element,
        id_attr: str,
        automation_id: str,
        aria_label: str,
        placeholder: str,
    ) -> str:
        """Attempt to find a human-readable label for an input element."""
        # aria-label is most reliable
        if aria_label:
            return aria_label

        # Look for an associated <label> by for="id"
        if id_attr:
            label_el = await page.query_selector(f'label[for="{id_attr}"]')
            if label_el:
                text = await label_el.inner_text()
                if text.strip():
                    return text.strip()

        # Look for a label that contains this element (wrapped label)
        label_text: Optional[str] = await element.evaluate(
            """el => {
                let node = el.parentNode;
                while (node && node !== document.body) {
                    if (node.tagName === 'LABEL') return node.textContent.trim();
                    const lbl = node.querySelector('label');
                    if (lbl) return lbl.textContent.trim();
                    node = node.parentNode;
                }
                return null;
            }"""
        )
        if label_text:
            return label_text

        # Fall back to placeholder or automation-id
        return placeholder or automation_id or ""
