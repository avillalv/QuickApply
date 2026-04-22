import asyncio
import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FormField:
    name: str
    label: str
    field_type: str  # "text" | "email" | "tel" | "select" | "checkbox" | "radio" | "textarea" | "file"
    value: Optional[str] = None
    options: list[str] = field(default_factory=list)
    required: bool = False
    filled: bool = False
    needs_review: bool = False
    confidence: float = 0.0
    selector: Optional[str] = None  # CSS selector hint for fill_field

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
        self.typing_delay: int = 60  # ms per character

    # ------------------------------------------------------------------
    # Subclass interface
    # ------------------------------------------------------------------

    async def detect_platform(self, url: str) -> str:
        raise NotImplementedError

    async def navigate_to_apply(self, page) -> None:
        raise NotImplementedError

    async def get_form_fields(self, page) -> list[FormField]:
        """
        Scan the current page for form fields, map values from profile,
        and fill fields that have high-confidence mappings.
        Returns all FormField objects (filled=True or needs_review=True).
        """
        raise NotImplementedError

    async def fill_field(self, page, form_field: FormField, value: str) -> None:
        raise NotImplementedError

    async def upload_resume(self, page, file_path: str) -> None:
        raise NotImplementedError

    async def next_page(self, page) -> bool:
        """Click Next/Continue. Returns True if there are more pages."""
        raise NotImplementedError

    async def submit(self, page) -> bool:
        """Submit the form. Returns True on success."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Shared utilities
    # ------------------------------------------------------------------

    async def human_type(self, page, selector: str, text: str) -> None:
        """Type text into a field character by character with randomised delay."""
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
            # Fall back to fill() for speed
            try:
                await page.fill(selector, text)
            except Exception:
                pass

    async def handle_select(self, page, selector: str, value: str) -> bool:
        """Handle a native <select> element."""
        try:
            await page.select_option(selector, label=value)
            return True
        except Exception:
            try:
                await page.select_option(selector, value=value)
                return True
            except Exception:
                return False

    async def handle_dropdown(self, page, selector: str, value: str) -> None:
        """Handle custom dropdown (click, wait for options, pick best match)."""
        try:
            await page.click(selector, timeout=5000)
        except Exception:
            return

        await asyncio.sleep(0.3)

        # Try native select first
        if await self.handle_select(page, selector, value):
            return

        # Try listbox options
        option_selectors = [
            f"[role='option']:has-text('{value}')",
            f"li[role='option']:has-text('{value}')",
            f".dropdown-option:has-text('{value}')",
            f"[data-value='{value}']",
        ]
        for sel in option_selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    await el.click()
                    return
            except Exception:
                pass

        # Fuzzy match: find best matching option text
        try:
            options = await page.query_selector_all("[role='option'], li[role='option']")
            best_el = None
            best_score = 0.0
            val_lower = value.lower()
            for opt in options:
                text = (await opt.inner_text()).strip().lower()
                if val_lower in text:
                    score = len(val_lower) / len(text) if text else 0
                    if score > best_score:
                        best_score = score
                        best_el = opt
            if best_el:
                await best_el.click()
        except Exception:
            pass

    async def handle_radio_or_checkbox(self, page, name: str, value: str) -> bool:
        """Click a radio/checkbox whose label matches value."""
        truthy = value.lower() in ("yes", "true", "1", "y")
        try:
            # Try by label text
            label_sel = f"label:has-text('{value}')"
            el = await page.query_selector(label_sel)
            if el:
                await el.click()
                return True
            # Try by input value
            inp = await page.query_selector(f"input[name='{name}'][value='{value}']")
            if inp:
                await inp.click()
                return True
            # Yes/No radios
            if truthy:
                for val in ("Yes", "yes", "Y", "True", "true"):
                    inp = await page.query_selector(f"input[name='{name}'][value='{val}']")
                    if inp:
                        await inp.click()
                        return True
            else:
                for val in ("No", "no", "N", "False", "false"):
                    inp = await page.query_selector(f"input[name='{name}'][value='{val}']")
                    if inp:
                        await inp.click()
                        return True
        except Exception:
            pass
        return False

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
        """Extract a string value from profile by key with bool conversion."""
        from utils.field_mapper import FieldMapper
        return FieldMapper(self.profile)._get_profile_value(key)

    async def _get_label_for_element(self, page, element) -> str:
        """Find the label text associated with a form element."""
        return await page.evaluate("""el => {
            if (el.id) {
                const lbl = document.querySelector(`label[for="${el.id}"]`);
                if (lbl) return lbl.innerText.trim();
            }
            const aria = el.getAttribute('aria-label') || el.getAttribute('aria-labelledby');
            if (aria) {
                const ref = document.getElementById(aria);
                return ref ? ref.innerText.trim() : aria.trim();
            }
            let node = el.parentNode;
            while (node && node !== document.body) {
                if (node.tagName === 'LABEL') return node.innerText.replace(el.value||'','').trim();
                const lbl = node.querySelector('label, .label, [class*="label"], legend');
                if (lbl && !lbl.contains(el)) return lbl.innerText.trim();
                node = node.parentNode;
            }
            return el.placeholder || el.name || '';
        }""", element)
