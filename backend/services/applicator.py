"""
Application automation orchestrator with co-pilot support.

Architecture:
  POST /api/automation/start → Creates AutomationSession → Launches asyncio background task
  WS  /ws?session=<id>       → Frontend receives events; sends proceed/abort/captcha_solved
"""

import asyncio
import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import WebSocket

# ---------------------------------------------------------------------------
# WebSocket Manager — routes by session_id
# ---------------------------------------------------------------------------

class WebSocketManager:
    def __init__(self):
        self._conns: dict[str, list[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket, session_id: str):
        await ws.accept()
        async with self._lock:
            self._conns.setdefault(session_id, []).append(ws)

    async def disconnect(self, ws: WebSocket, session_id: str):
        async with self._lock:
            bucket = self._conns.get(session_id, [])
            try:
                bucket.remove(ws)
            except ValueError:
                pass

    async def broadcast(self, msg: dict, session_id: str):
        dead: list[WebSocket] = []
        async with self._lock:
            targets = list(self._conns.get(session_id, []))
        for ws in targets:
            try:
                await ws.send_json(msg)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    for lst in self._conns.values():
                        try:
                            lst.remove(ws)
                        except ValueError:
                            pass

    async def route_message(self, msg: dict, session_id: str):
        session = get_session(session_id)
        if session:
            await session.receive_from_client(msg)


ws_manager = WebSocketManager()

# ---------------------------------------------------------------------------
# Session registry
# ---------------------------------------------------------------------------

_sessions: dict[str, "AutomationSession"] = {}


def get_session(session_id: str) -> Optional["AutomationSession"]:
    return _sessions.get(session_id)


def register_session(session: "AutomationSession"):
    _sessions[session.session_id] = session


def cleanup_session(session_id: str):
    _sessions.pop(session_id, None)


# ---------------------------------------------------------------------------
# AutomationSession
# ---------------------------------------------------------------------------

class AutomationSession:
    """Manages state for one automation run."""

    def __init__(self, session_id: str, mode: str, profile: dict,
                 resumes: list[dict], settings: dict):
        self.session_id = session_id
        self.mode = mode
        self.profile = profile
        self.resumes = resumes
        self.settings = settings
        self.status = "starting"
        self.current_page = 0
        self.application_id: Optional[str] = None  # set by router after DB insert
        self.task: Optional[asyncio.Task] = None
        self._queue: asyncio.Queue = asyncio.Queue()
        self.created_at = datetime.now().isoformat()

    async def broadcast(self, msg: dict):
        msg.setdefault("session_id", self.session_id)
        await ws_manager.broadcast(msg, self.session_id)

    async def log(self, text: str, level: str = "info"):
        await self.broadcast({"type": "log", "level": level, "text": text})

    async def wait_for_user(self) -> dict:
        self.status = "waiting"
        result = await self._queue.get()
        if result.get("action") != "abort":
            self.status = "running"
        return result

    async def receive_from_client(self, msg: dict):
        action = msg.get("type")
        if action == "proceed":
            await self._queue.put({"action": "proceed", "overrides": msg.get("overrides", [])})
        elif action == "abort":
            self.status = "aborted"
            await self._queue.put({"action": "abort"})
        elif action in ("auto_proceed", "captcha_solved", "login_done"):
            await self._queue.put({"action": "proceed", "overrides": []})

    def get_resume_path(self, label: str) -> Optional[str]:
        filename = label.replace(" ", "_") + ".pdf"
        path = os.path.join(os.path.dirname(__file__), "..", "..", "resumes", filename)
        abs_path = os.path.abspath(path)
        return abs_path if os.path.exists(abs_path) else None


# ---------------------------------------------------------------------------
# DB helper — update application record after submit
# ---------------------------------------------------------------------------

async def _update_application_status(app_id: str, status: str, answers: dict) -> None:
    """Update the tracker record with final status and any captured answers."""
    try:
        from database import get_supabase
        from datetime import timezone
        sb = get_supabase()
        data: dict = {
            "status": status,
            "last_status_update": datetime.now(timezone.utc).isoformat(),
        }
        if answers:
            data["answers_given"] = answers
        sb.table("applications").update(data).eq("id", app_id).execute()
    except Exception:
        pass  # non-fatal — record already exists with correct data


# ---------------------------------------------------------------------------
# Edge-case detection helpers
# ---------------------------------------------------------------------------

async def _detect_captcha(page) -> str | None:
    indicators = await page.evaluate("""() => {
        if (document.querySelector('iframe[src*="recaptcha"]')) return 'reCAPTCHA';
        if (document.querySelector('iframe[src*="hcaptcha"]')) return 'hCaptcha';
        if (document.querySelector('.cf-challenge-running, #cf-challenge-body, .cf-browser-verification')) return 'Cloudflare';
        if (document.querySelector('.g-recaptcha, #hcaptcha')) return 'CAPTCHA';
        if (document.querySelector('img[alt*="captcha" i], input[name*="captcha" i]')) return 'Image CAPTCHA';
        return null;
    }""")
    return indicators


async def _detect_login_wall(page) -> bool:
    result = await page.evaluate("""() => {
        const hasPassword = document.querySelector('input[type="password"]');
        if (!hasPassword) return false;
        const hasApplyForm = document.querySelector(
            'input[name="first_name"], input[name="firstName"], ' +
            '[data-automation-id="legalNameSection_firstName"], ' +
            '.application-form, #application-form'
        );
        return hasPassword && !hasApplyForm;
    }""")
    return bool(result)


async def _detect_already_applied(page) -> bool:
    text = (await page.evaluate("() => document.body.innerText")).lower()
    patterns = [
        "already applied", "you've already applied", "you have already applied",
        "application already submitted", "duplicate application",
        "previously applied", "application on file",
    ]
    return any(p in text for p in patterns)


async def _detect_confirmation(page) -> bool:
    text = (await page.evaluate("() => document.body.innerText")).lower()
    patterns = [
        "thank you for applying", "application received",
        "application submitted", "successfully submitted",
        "application complete", "we've received your application",
        "confirmation number", "application id:", "application reference",
        "you're done", "application has been sent",
    ]
    return any(p in text for p in patterns)


async def _get_validation_errors(page) -> list[str]:
    errors = await page.evaluate("""() => {
        const selectors = [
            '.error-message', '.field-error', '.validation-error',
            '[class*="error"]:not([class*="error-icon"])',
            '[class*="invalid"]', '.alert-danger', '.form-error',
            '[aria-invalid="true"]',
            '.input-feedback.error', '.helper-text--error',
        ];
        const seen = new Set();
        const msgs = [];
        for (const sel of selectors) {
            for (const el of document.querySelectorAll(sel)) {
                const text = el.innerText.trim();
                if (text && text.length < 200 && !seen.has(text)) {
                    seen.add(text);
                    msgs.push(text);
                }
            }
        }
        return msgs;
    }""")
    return errors or []


async def _take_screenshot(page, session_id: str, label: str) -> Optional[str]:
    try:
        screenshots_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "screenshots")
        )
        os.makedirs(screenshots_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(screenshots_dir, f"{session_id[:8]}_{label}_{ts}.png")
        await page.screenshot(path=path, full_page=False)
        return path
    except Exception:
        return None


async def _wait_for_page_stable(page, timeout: int = 15000):
    """Fast page-stable check: domcontentloaded only; skip networkidle (too slow)."""
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=timeout)
    except Exception:
        pass
    await asyncio.sleep(0.25)


# ---------------------------------------------------------------------------
# ApplicationAutomator
# ---------------------------------------------------------------------------

class ApplicationAutomator:
    """Runs a job application in a background asyncio.Task."""

    def __init__(self, session: AutomationSession):
        self.session = session

    async def run(self, job_url: str, resume_label: str,
                  job_data: dict, application_id: str) -> dict:
        session = self.session
        answers_collected: dict = {}

        try:
            session.status = "running"

            from services.scraper import detect_ats_platform
            ats = job_data.get("ats_platform") or detect_ats_platform(job_url)
            handler = self._get_handler(ats)
            resume_path = session.get_resume_path(resume_label)

            await session.log(
                f"Starting {session.mode.replace('_', ' ')} — "
                f"{job_data.get('job_title', 'position')} at "
                f"{job_data.get('company', 'company')} ({ats})"
            )

            headless = session.settings.get("browser_visible", "true") != "true"
            typing_delay = int(session.settings.get("typing_speed_ms", "35"))
            handler.typing_delay = typing_delay

            from playwright.async_api import async_playwright
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(
                    headless=headless,
                    args=[
                        "--no-sandbox",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-web-security",
                        "--no-first-run",
                        "--no-default-browser-check",
                    ],
                )
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1280, "height": 900},
                    ignore_https_errors=True,
                )
                await context.add_init_script(
                    "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
                )
                page = await context.new_page()
                handler.page = page

                context.on("page", lambda new_page: asyncio.create_task(
                    self._on_new_page(new_page, handler, session)
                ))

                await session.log(f"Opening {job_url}")
                try:
                    await page.goto(job_url, timeout=25000, wait_until="domcontentloaded")
                    await asyncio.sleep(0.5)
                except Exception as e:
                    await session.log(f"Navigation warning: {e}", "warn")

                # Check for already-applied
                if await _detect_already_applied(page):
                    await session.broadcast({
                        "type": "already_applied",
                        "application_id": session.application_id,
                        "text": "Already applied for this job.",
                    })
                    await browser.close()
                    session.status = "complete"
                    return {"success": False, "status": "already_applied"}

                # Navigate to apply form
                await session.log("Navigating to apply form…")
                try:
                    await handler.navigate_to_apply(page)
                    pages = context.pages
                    if len(pages) > 1:
                        page = pages[-1]
                        handler.page = page
                        await _wait_for_page_stable(page)
                except Exception as e:
                    await session.log(f"Navigate to apply: {e}", "warn")

                # Check for login wall
                if await _detect_login_wall(page):
                    await session.broadcast({
                        "type": "login_required",
                        "text": "Login required. Sign in, then click Continue.",
                    })
                    result = await session.wait_for_user()
                    if result.get("action") == "abort":
                        await browser.close()
                        session.status = "aborted"
                        return {"success": False, "status": "aborted"}
                    await _wait_for_page_stable(page)

                # Upload resume
                if resume_path:
                    try:
                        await handler.upload_resume(page, resume_path)
                        await session.log(f"Resume: {resume_label}")
                    except Exception as e:
                        await session.log(f"Resume upload skipped: {e}", "warn")

                # Multi-page loop
                page_num = 1
                max_pages = 20

                while page_num <= max_pages:
                    session.current_page = page_num

                    captcha_type = await _detect_captcha(page)
                    if captcha_type:
                        await _take_screenshot(page, session.session_id, "captcha")
                        await session.broadcast({
                            "type": "captcha_detected",
                            "captcha_type": captcha_type,
                            "text": f"{captcha_type} — solve in browser, then Continue.",
                        })
                        result = await session.wait_for_user()
                        if result.get("action") == "abort":
                            await browser.close()
                            session.status = "aborted"
                            return {"success": False, "status": "aborted"}
                        await _wait_for_page_stable(page)

                    if await _detect_confirmation(page):
                        if session.application_id:
                            await _update_application_status(
                                session.application_id, "Applied", answers_collected
                            )
                        await session.broadcast({
                            "type": "complete", "success": True,
                            "application_id": session.application_id,
                            "text": "Application submitted! Saved to Tracker.",
                        })
                        await browser.close()
                        session.status = "complete"
                        return {"success": True, "status": "complete"}

                    await session.broadcast({
                        "type": "step_start", "page": page_num,
                        "label": f"Page {page_num}",
                    })

                    try:
                        fields = await handler.get_form_fields(page)
                    except Exception as e:
                        await session.log(f"Field scan error: {e}", "warn")
                        fields = []

                    filled = [f.to_dict() for f in fields if f.filled and not f.needs_review]
                    needs_review = [f.to_dict() for f in fields if f.needs_review]

                    # Accumulate answers for tracker record
                    for f in fields:
                        if f.filled and f.value:
                            answers_collected[f.label or f.name] = f.value

                    await session.broadcast({
                        "type": "page_ready", "page": page_num,
                        "filled": filled, "needs_review": needs_review,
                        "url": page.url,
                    })

                    if session.mode == "copilot":
                        result = await session.wait_for_user()
                        if result.get("action") == "abort":
                            await session.broadcast({"type": "aborted"})
                            await browser.close()
                            session.status = "aborted"
                            return {"success": False, "status": "aborted"}

                        for override in result.get("overrides", []):
                            matching = next(
                                (f for f in fields if f.name == override.get("name")), None
                            )
                            if matching and override.get("value") is not None:
                                try:
                                    await handler.fill_field(page, matching, override["value"])
                                    answers_collected[matching.label or matching.name] = override["value"]
                                except Exception as e:
                                    await session.log(f"Override fill failed ({matching.name}): {e}", "warn")

                    try:
                        has_next = await handler.next_page(page)
                    except Exception as e:
                        await session.log(f"Next page error: {e}", "warn")
                        has_next = False

                    if not has_next:
                        break

                    await asyncio.sleep(0.3)
                    errors = await _get_validation_errors(page)
                    if errors:
                        await session.log(f"Form errors: {'; '.join(errors[:3])}", "warn")
                        await session.broadcast({
                            "type": "validation_errors", "errors": errors, "page": page_num,
                        })
                        continue

                    page_num += 1
                    await _wait_for_page_stable(page)

                # Submit phase
                if await _detect_confirmation(page):
                    if session.application_id:
                        await _update_application_status(
                            session.application_id, "Applied", answers_collected
                        )
                    await session.broadcast({
                        "type": "complete", "success": True,
                        "application_id": session.application_id,
                        "text": "Application submitted! Saved to Tracker.",
                    })
                    await browser.close()
                    session.status = "complete"
                    return {"success": True, "status": "complete"}

                await session.broadcast({
                    "type": "ready_to_submit", "page": page_num,
                    "message": "All pages filled. Review then submit.",
                })

                auto_submit = session.settings.get("auto_submit", "false") == "true"

                if session.mode == "copilot" and not auto_submit:
                    result = await session.wait_for_user()
                    if result.get("action") == "abort":
                        await session.broadcast({"type": "aborted"})
                        await browser.close()
                        session.status = "aborted"
                        return {"success": False, "status": "aborted"}

                if auto_submit or session.mode == "full_auto":
                    submitted = await handler.submit(page)
                    await asyncio.sleep(1.5)
                    if await _detect_confirmation(page):
                        submitted = True
                else:
                    submitted = True  # user clicked submit manually in browser

                if submitted and session.application_id:
                    await _update_application_status(
                        session.application_id, "Applied", answers_collected
                    )

                await session.broadcast({
                    "type": "complete",
                    "success": submitted,
                    "application_id": session.application_id,
                    "text": "Application submitted! Saved to Tracker." if submitted
                            else "Submission step reached — verify in browser.",
                })

                await context.close()
                await browser.close()
                session.status = "complete"
                return {"success": submitted, "status": "complete"}

        except asyncio.CancelledError:
            await session.broadcast({"type": "aborted", "text": "Session cancelled."})
            session.status = "aborted"
            return {"success": False, "status": "cancelled"}
        except Exception as exc:
            await session.log(f"Fatal error: {exc}", "error")
            await session.broadcast({"type": "error", "text": str(exc)})
            session.status = "error"
            return {"success": False, "status": "error", "error": str(exc)}
        finally:
            cleanup_session(session.session_id)

    async def _on_new_page(self, new_page, handler, session: AutomationSession):
        try:
            await new_page.wait_for_load_state("domcontentloaded", timeout=8000)
            handler.page = new_page
            await session.log("Switched to new tab.", "info")
        except Exception:
            pass

    def _get_handler(self, ats: str):
        from handlers.workday import WorkdayHandler
        from handlers.greenhouse import GreenhouseHandler
        from handlers.lever import LeverHandler
        from handlers.icims import ICIMSHandler
        from handlers.smartrecruiters import SmartRecruitersHandler
        from handlers.ashby import AshbyHandler
        from handlers.bamboohr import BambooHRHandler
        from handlers.generic import GenericHandler

        p, m = self.session.profile, self.session.mode
        ats_lower = ats.lower()
        if "workday" in ats_lower:   return WorkdayHandler(p, m)
        if "greenhouse" in ats_lower: return GreenhouseHandler(p, m)
        if "lever" in ats_lower:     return LeverHandler(p, m)
        if "icims" in ats_lower:     return ICIMSHandler(p, m)
        if "smartrecruiter" in ats_lower: return SmartRecruitersHandler(p, m)
        if "ashby" in ats_lower:     return AshbyHandler(p, m)
        if "bamboo" in ats_lower:    return BambooHRHandler(p, m)
        return GenericHandler(p, m)
