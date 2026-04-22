"""
Application automation orchestrator with proper session-based co-pilot support.

Architecture:
  POST /api/automation/start
    → Creates an AutomationSession
    → Launches asyncio background task
    → Returns session_id immediately

  WS /ws?session=<session_id>
    → Frontend connects after getting session_id
    → Background task broadcasts page status to this session
    → Frontend sends {type:"proceed", overrides:[...]} to resume

  The background task pauses at each page via asyncio.Queue.get()
  and waits for the user's "proceed" message before advancing.
"""

import asyncio
import uuid
from typing import Optional
from datetime import datetime

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
        """Route an incoming client WebSocket message to its session."""
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
    """
    Manages state for one automation run.

    The Playwright background task calls wait_for_user() to pause between
    pages.  When the user clicks "Proceed" in the overlay, receive_from_client()
    puts a signal on the queue and the task resumes.
    """

    def __init__(
        self,
        session_id: str,
        mode: str,
        profile: dict,
        resumes: list[dict],
        settings: dict,
    ):
        self.session_id = session_id
        self.mode = mode
        self.profile = profile
        self.resumes = resumes
        self.settings = settings
        self.status = "starting"
        self.current_page = 0
        self.task: Optional[asyncio.Task] = None
        self._queue: asyncio.Queue = asyncio.Queue()
        self.created_at = datetime.now().isoformat()

    # ------------------------------------------------------------------
    # Communication helpers
    # ------------------------------------------------------------------

    async def broadcast(self, msg: dict):
        msg.setdefault("session_id", self.session_id)
        await ws_manager.broadcast(msg, self.session_id)

    async def log(self, text: str, level: str = "info"):
        await self.broadcast({"type": "log", "level": level, "text": text})

    async def wait_for_user(self) -> dict:
        """Pause the automation task until the user sends a proceed/abort signal."""
        self.status = "waiting"
        result = await self._queue.get()
        if result.get("action") != "abort":
            self.status = "running"
        return result

    async def receive_from_client(self, msg: dict):
        action = msg.get("type")
        if action == "proceed":
            await self._queue.put({
                "action": "proceed",
                "overrides": msg.get("overrides", []),
            })
        elif action == "abort":
            self.status = "aborted"
            await self._queue.put({"action": "abort"})
        elif action == "auto_proceed":
            await self._queue.put({"action": "proceed", "overrides": []})

    # ------------------------------------------------------------------
    # Profile helpers
    # ------------------------------------------------------------------

    def get_resume_text(self, label: str) -> str:
        for r in self.resumes:
            if r.get("label") == label:
                return r.get("parsed_text") or ""
        return ""

    def get_resume_path(self, label: str) -> Optional[str]:
        import os
        filename = label.replace(" ", "_") + ".pdf"
        path = os.path.join(
            os.path.dirname(__file__), "..", "..", "resumes", filename
        )
        return os.path.abspath(path) if os.path.exists(os.path.abspath(path)) else None


# ---------------------------------------------------------------------------
# ApplicationAutomator
# ---------------------------------------------------------------------------

class ApplicationAutomator:
    """
    Runs a job application end-to-end in a background asyncio.Task.
    Communicates with the frontend overlay via AutomationSession.
    """

    def __init__(self, session: AutomationSession):
        self.session = session

    async def run(
        self,
        job_url: str,
        resume_label: str,
        job_data: dict,
        application_id: str,
    ) -> dict:
        session = self.session

        try:
            session.status = "running"

            from services.scraper import detect_ats_platform
            ats = job_data.get("ats_platform") or detect_ats_platform(job_url)
            handler = self._get_handler(ats)
            resume_path = session.get_resume_path(resume_label)

            await session.log(
                f"Starting {session.mode.replace('_', ' ')} — "
                f"{job_data.get('job_title', 'position')} at "
                f"{job_data.get('company', 'company')} via {ats}"
            )

            headless = session.settings.get("browser_visible", "true") != "true"
            typing_delay = int(session.settings.get("typing_speed_ms", "60"))
            handler.typing_delay = typing_delay

            from playwright.async_api import async_playwright
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(
                    headless=headless,
                    args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
                )
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1280, "height": 900},
                )
                await context.add_init_script(
                    "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
                )
                page = await context.new_page()
                handler.page = page

                await session.log(f"Navigating to {job_url}")
                await page.goto(job_url, timeout=30000, wait_until="domcontentloaded")
                try:
                    await page.wait_for_load_state("networkidle", timeout=8000)
                except Exception:
                    pass

                await session.log("Looking for Apply button…")
                await handler.navigate_to_apply(page)

                # Upload resume on first page (before scanning fields)
                if resume_path:
                    try:
                        await handler.upload_resume(page, resume_path)
                        await session.log(f"Resume uploaded: {resume_label}")
                    except Exception as e:
                        await session.log(f"Resume upload skipped: {e}", "warn")

                page_num = 1
                while True:
                    session.current_page = page_num
                    await session.broadcast({
                        "type": "step_start",
                        "page": page_num,
                        "label": f"Page {page_num}",
                    })

                    # Scan + fill page
                    fields = await handler.get_form_fields(page)
                    filled, needs_review = [], []
                    for f in fields:
                        if f.field_type == "file":
                            continue
                        if f.filled:
                            filled.append(f.to_dict())
                        elif f.needs_review:
                            needs_review.append(f.to_dict())

                    await session.broadcast({
                        "type": "page_ready",
                        "page": page_num,
                        "filled": filled,
                        "needs_review": needs_review,
                    })

                    if session.mode == "copilot":
                        result = await session.wait_for_user()
                        if result.get("action") == "abort":
                            await session.broadcast({"type": "aborted"})
                            await browser.close()
                            session.status = "aborted"
                            return {"success": False, "status": "aborted"}

                        # Apply user overrides to browser form
                        for override in result.get("overrides", []):
                            matching = next(
                                (f for f in fields if f.name == override.get("name")), None
                            )
                            if matching and override.get("value"):
                                try:
                                    await handler.fill_field(page, matching, override["value"])
                                except Exception as e:
                                    await session.log(f"Override fill failed for {matching.name}: {e}", "warn")

                    has_next = await handler.next_page(page)
                    if not has_next:
                        break
                    page_num += 1

                    # Wait for next page to fully load
                    try:
                        await page.wait_for_load_state("networkidle", timeout=15000)
                    except Exception:
                        pass
                    await asyncio.sleep(0.5)

                # --- Final submit step ---
                await session.broadcast({
                    "type": "ready_to_submit",
                    "page": page_num,
                    "message": "All pages complete. Ready to submit application.",
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
                else:
                    submitted = True  # User will click submit manually in browser

                await session.broadcast({
                    "type": "complete",
                    "success": submitted,
                    "text": (
                        "Application submitted successfully!"
                        if submitted
                        else "Submission step reached — check the browser to confirm."
                    ),
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
            await session.broadcast({"type": "error", "text": str(exc)})
            session.status = "error"
            return {"success": False, "status": "error", "error": str(exc)}
        finally:
            cleanup_session(session.session_id)

    def _get_handler(self, ats: str):
        from handlers.workday import WorkdayHandler
        from handlers.greenhouse import GreenhouseHandler
        from handlers.lever import LeverHandler
        from handlers.generic import GenericHandler

        p, m = self.session.profile, self.session.mode
        ats_lower = ats.lower()
        if "workday" in ats_lower:
            return WorkdayHandler(p, m)
        if "greenhouse" in ats_lower:
            return GreenhouseHandler(p, m)
        if "lever" in ats_lower:
            return LeverHandler(p, m)
        return GenericHandler(p, m)
