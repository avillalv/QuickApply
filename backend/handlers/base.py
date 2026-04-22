import asyncio
import re
import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FormField:
    name: str
    label: str
    field_type: str  # text|email|tel|select|checkbox|radio|textarea|file|date
    value: Optional[str] = None
    options: list[str] = field(default_factory=list)
    required: bool = False
    filled: bool = False
    needs_review: bool = False
    confidence: float = 0.0
    selector: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "label": self.label,
            "field_type": self.field_type,
            "value": self.value,
            "options": self.options or [],
            "required": self.required,
            "filled": self.filled,
            "needs_review": self.needs_review,
            "confidence": round(self.confidence, 2),
        }


class ATSHandler:
    """Base class for all ATS application handlers."""

    def __init__(self, profile: dict, mode: str = "copilot") -> None:
        self.profile = profile
        self.mode = mode
        self.page = None
        self.typing_delay: int = 60

    # ------------------------------------------------------------------
    # Subclass interface
    # ------------------------------------------------------------------

    async def detect_platform(self, url: str) -> str:
        raise NotImplementedError

    async def navigate_to_apply(self, page) -> None:
        raise NotImplementedError

    async def get_form_fields(self, page) -> list[FormField]:
        raise NotImplementedError

    async def fill_field(self, page, form_field: FormField, value: str) -> None:
        raise NotImplementedError

    async def upload_resume(self, page, file_path: str) -> None:
        raise NotImplementedError

    async def next_page(self, page) -> bool:
        raise NotImplementedError

    async def submit(self, page) -> bool:
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Text input
    # ------------------------------------------------------------------

    async def human_type(self, page, selector: str, text: str) -> None:
        try:
            el = await page.wait_for_selector(selector, timeout=8000, state="visible")
            await el.click()
            await page.keyboard.press("Control+a")
            await page.keyboard.press("Delete")
            for char in text:
                await page.keyboard.type(char)
                jitter = random.uniform(0.5, 1.5)
                await asyncio.sleep((self.typing_delay * jitter) / 1000)
        except Exception:
            try:
                await page.fill(selector, text)
            except Exception:
                pass

    async def fill_text_field(self, page, selector: str, value: str) -> bool:
        """Fill a text/textarea field, trying fill() then JS dispatch."""
        if not value:
            return False
        try:
            await page.fill(selector, value)
            return True
        except Exception:
            pass
        try:
            el = await page.query_selector(selector)
            if el:
                await page.evaluate(
                    f"""el => {{
                        el.value = {repr(value)};
                        el.dispatchEvent(new Event('input', {{bubbles:true}}));
                        el.dispatchEvent(new Event('change', {{bubbles:true}}));
                    }}""",
                    el,
                )
                return True
        except Exception:
            pass
        return False

    # ------------------------------------------------------------------
    # Select / Dropdown
    # ------------------------------------------------------------------

    async def handle_select(self, page, selector: str, value: str) -> bool:
        """Handle <select> element by label or value."""
        try:
            await page.select_option(selector, label=value)
            return True
        except Exception:
            pass
        try:
            await page.select_option(selector, value=value)
            return True
        except Exception:
            pass
        # Try case-insensitive partial match via JS
        try:
            matched = await page.evaluate(f"""sel => {{
                const el = document.querySelector(sel);
                if (!el) return false;
                const val = {repr(value.lower())};
                for (const opt of el.options) {{
                    if (opt.text.toLowerCase().includes(val) || opt.value.toLowerCase().includes(val)) {{
                        el.value = opt.value;
                        el.dispatchEvent(new Event('change', {{bubbles:true}}));
                        return true;
                    }}
                }}
                return false;
            }}""", selector)
            return bool(matched)
        except Exception:
            return False

    async def handle_dropdown(self, page, trigger_selector: str, value: str) -> bool:
        """Handle custom (non-native) dropdown: click trigger, pick option."""
        try:
            await page.click(trigger_selector, timeout=5000)
        except Exception:
            return False

        await asyncio.sleep(0.4)

        # Try native select first
        if await self.handle_select(page, trigger_selector, value):
            return True

        val_lower = value.lower()

        # Try ARIA listbox options
        option_selectors = [
            f"[role='option']:has-text('{value}')",
            f"li[role='option']:has-text('{value}')",
            f".dropdown-option:has-text('{value}')",
            f"[data-value='{value}']",
            f"li:has-text('{value}')",
        ]
        for sel in option_selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    return True
            except Exception:
                pass

        # Fuzzy text match among visible options
        try:
            options = await page.query_selector_all(
                "[role='option'], li[role='option'], .select-option, li.option"
            )
            best_el = None
            best_score = 0.0
            for opt in options:
                try:
                    text = (await opt.inner_text()).strip().lower()
                    if val_lower in text:
                        score = len(val_lower) / max(len(text), 1)
                        if score > best_score:
                            best_score = score
                            best_el = opt
                except Exception:
                    pass
            if best_el and best_score > 0.3:
                await best_el.click()
                return True
        except Exception:
            pass

        return False

    # ------------------------------------------------------------------
    # Radio / Checkbox
    # ------------------------------------------------------------------

    async def handle_radio_or_checkbox(self, page, name: str, value: str) -> bool:
        truthy = value.lower() in ("yes", "true", "1", "y")
        try:
            # By label text
            for label_sel in [
                f"label:has-text('{value}')",
                f"label:has-text('{value.lower()}')",
            ]:
                el = await page.query_selector(label_sel)
                if el and await el.is_visible():
                    await el.click()
                    return True
            # By input value attribute
            inp = await page.query_selector(f"input[name='{name}'][value='{value}']")
            if inp:
                await inp.click()
                return True
            # Yes/No pattern
            candidates = ["Yes", "yes", "Y", "True", "true"] if truthy else ["No", "no", "N", "False", "false"]
            for val in candidates:
                inp = await page.query_selector(f"input[name='{name}'][value='{val}']")
                if inp:
                    await inp.click()
                    return True
        except Exception:
            pass
        return False

    # ------------------------------------------------------------------
    # Date picker
    # ------------------------------------------------------------------

    async def handle_date_field(self, page, selector: str, value: str) -> bool:
        """Handle both native date inputs and custom date pickers."""
        if not value:
            return False
        try:
            el = await page.query_selector(selector)
            if not el:
                return False

            input_type = await el.evaluate("e => e.type || ''")

            # Native date input (type="date") expects YYYY-MM-DD
            if input_type == "date":
                # Try to parse common formats into YYYY-MM-DD
                normalized = self._normalize_date(value)
                if normalized:
                    await page.fill(selector, normalized)
                    return True
                return False

            # Plain text date field
            if input_type in ("text", ""):
                await page.fill(selector, value)
                # Check if a calendar popup appeared
                await asyncio.sleep(0.3)
                closed = await self._close_date_picker(page)
                return True

        except Exception:
            pass
        return False

    def _normalize_date(self, value: str) -> Optional[str]:
        """Convert various date formats to YYYY-MM-DD."""
        import datetime
        formats = [
            "%B %Y", "%b %Y", "%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y",
            "%d/%m/%Y", "%Y/%m/%d", "%B %d, %Y", "%b %d, %Y",
        ]
        for fmt in formats:
            try:
                dt = datetime.datetime.strptime(value.strip(), fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        # "Immediately" → today
        if "immediate" in value.lower():
            return datetime.datetime.today().strftime("%Y-%m-%d")
        return None

    async def _close_date_picker(self, page) -> bool:
        """Close any calendar popup that appeared."""
        close_selectors = [
            "button.calendar-close", ".datepicker-close", "[aria-label='Close']",
            ".react-datepicker__close-icon",
        ]
        for sel in close_selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    await el.click()
                    return True
            except Exception:
                pass
        # Press Escape to close
        try:
            await page.keyboard.press("Escape")
        except Exception:
            pass
        return False

    # ------------------------------------------------------------------
    # Rich text / WYSIWYG
    # ------------------------------------------------------------------

    async def handle_rich_text(self, page, selector: str, value: str) -> bool:
        """Fill a contenteditable/rich-text field (e.g., Quill, Draft.js)."""
        if not value:
            return False
        try:
            el = await page.query_selector(selector)
            if not el:
                return False

            # Check if it's contenteditable
            ce = await el.get_attribute("contenteditable")
            if ce in ("true", ""):
                await el.click()
                await page.keyboard.press("Control+a")
                await page.keyboard.press("Delete")
                await el.type(value)
                return True

            # Quill editor
            quill = await page.query_selector(".ql-editor")
            if quill:
                await quill.click()
                await page.keyboard.press("Control+a")
                await page.keyboard.press("Delete")
                await quill.type(value)
                return True

            # Draft.js
            draft = await page.query_selector(".DraftEditor-editorContainer [contenteditable='true']")
            if draft:
                await draft.click()
                await page.keyboard.press("Control+a")
                await page.keyboard.press("Delete")
                await draft.type(value)
                return True

        except Exception:
            pass
        return False

    # ------------------------------------------------------------------
    # Phone number formatting
    # ------------------------------------------------------------------

    def format_phone(self, phone: str, format_hint: str = "") -> str:
        """Normalize phone number, optionally to a specific format."""
        if not phone:
            return ""
        # Strip to digits only
        digits = re.sub(r"\D", "", phone)
        if digits.startswith("1") and len(digits) == 11:
            digits = digits[1:]  # Remove US country code
        if len(digits) != 10:
            return phone  # Return original if we can't parse

        hint_lower = format_hint.lower()
        if "dash" in hint_lower or re.search(r"\d{3}-\d{3}-\d{4}", format_hint):
            return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
        if "dot" in hint_lower or "period" in hint_lower:
            return f"{digits[:3]}.{digits[3:6]}.{digits[6:]}"
        if "paren" in hint_lower or re.search(r"\(\d{3}\)", format_hint):
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        # Default: (555) 123-4567
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"

    # ------------------------------------------------------------------
    # Multi-select
    # ------------------------------------------------------------------

    async def handle_multiselect(self, page, selector: str, values: list[str]) -> bool:
        """Select multiple options in a <select multiple> or custom multi-select."""
        if not values:
            return False
        try:
            # Native multi-select
            await page.select_option(selector, label=values)
            return True
        except Exception:
            pass
        # Try clicking each option in a custom multi-select
        for val in values:
            try:
                opt_sel = f"[role='option']:has-text('{val}')"
                el = await page.query_selector(opt_sel)
                if el:
                    await el.click()
                    await asyncio.sleep(0.1)
            except Exception:
                pass
        return False

    # ------------------------------------------------------------------
    # Shared utilities
    # ------------------------------------------------------------------

    async def random_delay(self, min_ms: int = 200, max_ms: int = 600) -> None:
        await asyncio.sleep(random.randint(min_ms, max_ms) / 1000)

    async def click_and_wait(self, page, selector: str, timeout: int = 15000) -> bool:
        try:
            await page.click(selector, timeout=5000)
            await page.wait_for_load_state("domcontentloaded", timeout=timeout)
            return True
        except Exception:
            return False

    def _profile_value(self, key: str) -> Optional[str]:
        from utils.field_mapper import FieldMapper
        return FieldMapper(self.profile)._get_profile_value(key)

    async def _get_label_for_element(self, page, element) -> str:
        """Find the label text associated with a form element."""
        return await page.evaluate("""el => {
            if (el.id) {
                const lbl = document.querySelector(`label[for="${el.id}"]`);
                if (lbl) return lbl.innerText.trim();
            }
            const ariaLabel = el.getAttribute('aria-label');
            if (ariaLabel) return ariaLabel.trim();
            const ariaLabelledBy = el.getAttribute('aria-labelledby');
            if (ariaLabelledBy) {
                const ref = document.getElementById(ariaLabelledBy);
                if (ref) return ref.innerText.trim();
            }
            // Walk up DOM looking for label/legend
            let node = el.parentNode;
            for (let i = 0; i < 6 && node && node !== document.body; i++) {
                if (node.tagName === 'LABEL') return node.innerText.replace(el.value||'','').trim();
                const lbl = node.querySelector('label, legend, .label, .field-label, [class*="label"]:not(input)');
                if (lbl && !lbl.contains(el)) return lbl.innerText.trim();
                node = node.parentNode;
            }
            return el.placeholder || el.name || el.id || '';
        }""", element)

    async def _get_options_for_select(self, page, el) -> list[str]:
        """Return all option texts for a <select> element."""
        try:
            return await page.evaluate(
                "el => Array.from(el.options).map(o => o.text.trim()).filter(Boolean)", el
            )
        except Exception:
            return []

    async def scroll_into_view(self, page, selector: str) -> None:
        try:
            el = await page.query_selector(selector)
            if el:
                await el.scroll_into_view_if_needed()
        except Exception:
            pass
