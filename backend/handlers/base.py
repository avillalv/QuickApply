import asyncio
import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FormField:
    name: str
    label: str
    field_type: str  # "text", "select", "checkbox", "radio", "file", "textarea"
    value: Optional[str] = None
    options: list[str] = field(default_factory=list)
    required: bool = False
    filled: bool = False
    needs_review: bool = False


class ATSHandler:
    """Base class for all ATS-specific application handlers."""

    def __init__(self, profile: dict, mode: str = "copilot") -> None:
        self.profile = profile
        self.mode = mode
        self.page = None

    # ------------------------------------------------------------------
    # Abstract interface — subclasses must override these
    # ------------------------------------------------------------------

    async def detect_platform(self, url: str) -> str:
        """Return the ATS platform name detected from the URL."""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement detect_platform()"
        )

    async def navigate_to_apply(self, page) -> None:
        """Navigate the browser page to the apply form."""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement navigate_to_apply()"
        )

    async def get_form_fields(self, page) -> list[FormField]:
        """Return a list of FormField objects representing fields on the page."""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement get_form_fields()"
        )

    async def fill_field(self, page, form_field: FormField, value: str) -> None:
        """Fill a specific form field with the given value."""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement fill_field()"
        )

    async def upload_resume(self, page, file_path: str) -> None:
        """Upload the resume PDF file to the form."""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement upload_resume()"
        )

    async def next_page(self, page) -> bool:
        """
        Advance to the next page of a multi-step form.
        Returns False if this is the final page (ready to submit).
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement next_page()"
        )

    async def submit(self, page) -> bool:
        """Submit the completed application. Returns True on success."""
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement submit()"
        )

    # ------------------------------------------------------------------
    # Shared utility methods — subclasses can use these directly
    # ------------------------------------------------------------------

    async def handle_dropdown(self, page, selector: str, value: str) -> None:
        """
        Click a dropdown selector, wait for the option list to appear,
        then click the option whose text most closely matches *value*.
        """
        await page.click(selector)
        # Wait for at least one option to become visible
        await page.wait_for_selector("[role='option'], option, li[role='option']", timeout=5000)

        # Try <option> elements inside a <select> first
        option_selected = await page.evaluate(
            """([sel, val]) => {
                const selectEl = document.querySelector(sel);
                if (selectEl && selectEl.tagName === 'SELECT') {
                    const options = Array.from(selectEl.options);
                    const match = options.find(o =>
                        o.text.trim().toLowerCase().includes(val.toLowerCase())
                    );
                    if (match) { selectEl.value = match.value; selectEl.dispatchEvent(new Event('change', {bubbles: true})); return true; }
                }
                return false;
            }""",
            [selector, value],
        )

        if not option_selected:
            # Fall back to clicking a listbox option
            options = await page.query_selector_all(
                "[role='option'], li[role='option'], .dropdown-option"
            )
            for option in options:
                text = await option.inner_text()
                if value.lower() in text.strip().lower():
                    await option.click()
                    return

    async def human_type(
        self, page, selector: str, text: str, delay_ms: int = 75
    ) -> None:
        """
        Type *text* into *selector* character by character with randomized delay
        to simulate human typing and avoid bot-detection.
        """
        element = await page.wait_for_selector(selector, timeout=10000)
        await element.click()
        # Clear existing content
        await page.keyboard.press("Control+a")
        await page.keyboard.press("Delete")

        for char in text:
            await page.keyboard.type(char)
            # Randomize delay: ±40% of the base delay
            jitter = random.uniform(0.6, 1.4)
            await asyncio.sleep((delay_ms * jitter) / 1000)

    async def random_delay(self, min_ms: int = 200, max_ms: int = 800) -> None:
        """Sleep for a random duration between min_ms and max_ms milliseconds."""
        duration_ms = random.randint(min_ms, max_ms)
        await asyncio.sleep(duration_ms / 1000)
