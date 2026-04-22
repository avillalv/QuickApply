"""
Playwright-based job posting scraper.

Detects the ATS platform from the URL, launches a headless Chromium browser,
and extracts structured job data from the posting page.
"""

import re
from playwright.async_api import async_playwright


# ATS platform detection patterns: (platform_name, [url_regex_patterns])
_ATS_PATTERNS: list[tuple[str, list[str]]] = [
    ("Workday", [
        r"\.myworkdayjobs\.com",
        r"\.wd\d+\.myworkdaysite\.com",
        r"workday\.com/en-US/recruiting",
    ]),
    ("Greenhouse", [
        r"boards\.greenhouse\.io",
        r"job-boards\.greenhouse\.io",
        r"greenhouse\.io/",
    ]),
    ("Lever", [
        r"jobs\.lever\.co",
        r"lever\.co/",
    ]),
    ("iCIMS", [
        r"icims\.com",
        r"jobs\.icims\.com",
    ]),
    ("Taleo", [
        r"taleo\.net",
        r"\.taleo\.com",
    ]),
    ("SmartRecruiters", [
        r"jobs\.smartrecruiters\.com",
        r"smartrecruiters\.com/",
    ]),
    ("Ashby", [
        r"jobs\.ashbyhq\.com",
        r"ashbyhq\.com/",
    ]),
    ("BambooHR", [
        r"bamboohr\.com/careers",
        r"\.bamboohr\.com/jobs",
    ]),
    ("JazzHR", [
        r"app\.jazz\.co",
        r"\.jazz\.co/",
    ]),
    ("ADP", [
        r"adp\.com/careers",
        r"workforcenow\.adp\.com",
    ]),
]


def detect_ats_platform(url: str) -> str:
    """
    Detect the ATS platform from a job posting URL.

    Returns the platform name string, or "Custom ATS" if unrecognized.
    """
    for platform_name, patterns in _ATS_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return platform_name
    return "Custom ATS"


async def scrape_job_posting(url: str) -> dict:
    """
    Scrape a job posting page and return structured job data.

    Args:
        url: The URL of the job posting.

    Returns:
        A dict with keys: job_title, company, location, salary_range,
        job_description, ats_platform, raw_url.
    """
    ats_platform = detect_ats_platform(url)

    result = {
        "job_title": "",
        "company": "",
        "location": "",
        "salary_range": "",
        "job_description": "",
        "ats_platform": ats_platform,
        "raw_url": url,
    }

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        try:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_selector("body", timeout=30000)

            # Give JS-heavy pages a moment to render
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass  # Proceed even if networkidle times out

            # ----------------------------------------------------------------
            # Extract job title
            # ----------------------------------------------------------------
            title = await _extract_title(page)
            result["job_title"] = title

            # ----------------------------------------------------------------
            # Extract company name
            # ----------------------------------------------------------------
            company = await _extract_company(page)
            result["company"] = company

            # ----------------------------------------------------------------
            # Extract location
            # ----------------------------------------------------------------
            location = await _extract_location(page)
            result["location"] = location

            # ----------------------------------------------------------------
            # Extract salary range
            # ----------------------------------------------------------------
            salary = await _extract_salary(page)
            result["salary_range"] = salary

            # ----------------------------------------------------------------
            # Extract job description (main body text)
            # ----------------------------------------------------------------
            description = await _extract_description(page)
            result["job_description"] = description

        except Exception as exc:
            result["job_description"] = f"[Scrape error: {exc}]"
        finally:
            await context.close()
            await browser.close()

    return result


# ---------------------------------------------------------------------------
# Internal extraction helpers
# ---------------------------------------------------------------------------

async def _extract_title(page) -> str:
    """Try og:title meta, then page <title>, then first <h1>."""
    # og:title meta tag
    og_title = await page.evaluate(
        "() => { const el = document.querySelector('meta[property=\"og:title\"]'); "
        "return el ? el.getAttribute('content') : null; }"
    )
    if og_title and og_title.strip():
        return og_title.strip()

    # <title> tag
    page_title = await page.title()
    if page_title and page_title.strip():
        # Strip common suffixes like " - Company Name | Careers"
        title = re.split(r"\s*[|\-–—]\s*", page_title)[0].strip()
        if title:
            return title

    # First <h1>
    h1 = await page.evaluate(
        "() => { const el = document.querySelector('h1'); "
        "return el ? el.innerText.trim() : null; }"
    )
    if h1 and h1.strip():
        return h1.strip()

    return ""


async def _extract_company(page) -> str:
    """Try og:site_name, meta company tag, JSON-LD structured data, then heuristics."""
    # og:site_name
    og_site = await page.evaluate(
        "() => { const el = document.querySelector('meta[property=\"og:site_name\"]'); "
        "return el ? el.getAttribute('content') : null; }"
    )
    if og_site and og_site.strip():
        return og_site.strip()

    # <meta name="company"> or <meta name="organization">
    meta_company = await page.evaluate(
        "() => { "
        "  const names = ['company', 'organization', 'author']; "
        "  for (const n of names) { "
        "    const el = document.querySelector(`meta[name='${n}']`); "
        "    if (el && el.content) return el.content; "
        "  } "
        "  return null; "
        "}"
    )
    if meta_company and meta_company.strip():
        return meta_company.strip()

    # JSON-LD structured data
    company_from_ld = await page.evaluate(
        """() => {
            const scripts = document.querySelectorAll('script[type="application/ld+json"]');
            for (const s of scripts) {
                try {
                    const data = JSON.parse(s.textContent);
                    if (data.hiringOrganization && data.hiringOrganization.name)
                        return data.hiringOrganization.name;
                    if (data.organizer && data.organizer.name)
                        return data.organizer.name;
                } catch (e) {}
            }
            return null;
        }"""
    )
    if company_from_ld and company_from_ld.strip():
        return company_from_ld.strip()

    return ""


async def _extract_location(page) -> str:
    """Extract location from structured data or common element patterns."""
    # JSON-LD jobLocation
    location_ld = await page.evaluate(
        """() => {
            const scripts = document.querySelectorAll('script[type="application/ld+json"]');
            for (const s of scripts) {
                try {
                    const data = JSON.parse(s.textContent);
                    if (data.jobLocation) {
                        const loc = data.jobLocation;
                        if (typeof loc === 'string') return loc;
                        if (loc.address) {
                            const addr = loc.address;
                            const parts = [addr.addressLocality, addr.addressRegion, addr.addressCountry].filter(Boolean);
                            return parts.join(', ');
                        }
                    }
                } catch (e) {}
            }
            return null;
        }"""
    )
    if location_ld and location_ld.strip():
        return location_ld.strip()

    # Common element patterns
    location_el = await page.evaluate(
        """() => {
            const selectors = [
                '[data-automation-id="locations"]',
                '.location', '.job-location', '[class*="location"]',
                '[data-testid="location"]', '.posting-location',
                '[itemprop="jobLocation"]',
            ];
            for (const sel of selectors) {
                const el = document.querySelector(sel);
                if (el && el.innerText.trim()) return el.innerText.trim();
            }
            return null;
        }"""
    )
    if location_el and location_el.strip():
        return location_el.strip()

    return ""


async def _extract_salary(page) -> str:
    """Look for salary/compensation information in structured data or page text."""
    # JSON-LD baseSalary
    salary_ld = await page.evaluate(
        """() => {
            const scripts = document.querySelectorAll('script[type="application/ld+json"]');
            for (const s of scripts) {
                try {
                    const data = JSON.parse(s.textContent);
                    if (data.baseSalary) {
                        const bs = data.baseSalary;
                        if (typeof bs === 'string') return bs;
                        if (bs.value) {
                            if (bs.value.minValue && bs.value.maxValue)
                                return `$${bs.value.minValue} - $${bs.value.maxValue}`;
                            if (bs.value.value) return `$${bs.value.value}`;
                        }
                    }
                } catch (e) {}
            }
            return null;
        }"""
    )
    if salary_ld and salary_ld.strip():
        return salary_ld.strip()

    # Look for salary patterns in page text
    body_text = await page.evaluate("() => document.body.innerText")
    salary_match = re.search(
        r"\$[\d,]+(?:\s*[-–—]\s*\$[\d,]+)?(?:\s*(?:per\s+)?(?:year|yr|hour|hr|k))?",
        body_text,
        re.IGNORECASE,
    )
    if salary_match:
        return salary_match.group(0).strip()

    return ""


async def _extract_description(page) -> str:
    """Extract the main job description text content."""
    # Try known job description containers
    description = await page.evaluate(
        """() => {
            const selectors = [
                '[data-automation-id="jobPostingDescription"]',
                '#job-description', '.job-description',
                '[class*="jobDescription"]', '[class*="job-description"]',
                '[class*="description"]', '.posting-description',
                '[itemprop="description"]',
                'article', 'main',
            ];
            for (const sel of selectors) {
                const el = document.querySelector(sel);
                if (el) {
                    const text = el.innerText.trim();
                    if (text.length > 100) return text;
                }
            }
            return null;
        }"""
    )

    if description and description.strip():
        return _clean_text(description)

    # Fall back to full body text (strip navigation/header noise)
    body_text = await page.evaluate(
        """() => {
            // Remove script, style, nav, header, footer elements
            const clone = document.body.cloneNode(true);
            for (const tag of ['script', 'style', 'nav', 'header', 'footer', 'noscript']) {
                for (const el of clone.querySelectorAll(tag)) el.remove();
            }
            return clone.innerText;
        }"""
    )
    return _clean_text(body_text) if body_text else ""


def _clean_text(text: str) -> str:
    """Remove excess whitespace and normalize newlines."""
    if not text:
        return ""
    # Normalize unicode whitespace
    text = text.replace("\xa0", " ").replace("​", "")
    # Collapse horizontal whitespace
    text = re.sub(r"[ \t]+", " ", text)
    # Collapse excess blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip each line
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(lines).strip()
