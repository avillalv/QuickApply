"""
Application automation orchestrator.

ApplicationAutomator drives the end-to-end job application workflow by:
1. Detecting the ATS platform.
2. Selecting the appropriate ATSHandler subclass.
3. Launching the browser, navigating to the form, filling fields,
   uploading the resume, and submitting.

WebSocketManager provides a broadcast channel so the Playwright worker can
push live status updates to the React co-pilot dashboard.
"""

import asyncio
from typing import Optional

from fastapi import WebSocket

from handlers.base import ATSHandler
from handlers.workday import WorkdayHandler
from handlers.greenhouse import GreenhouseHandler
from handlers.lever import LeverHandler
from handlers.generic import GenericHandler
from services.scraper import detect_ats_platform


class WebSocketManager:
    """
    Manages active WebSocket connections for co-pilot mode.

    The Playwright automation worker calls broadcast() to push JSON
    status messages to all connected dashboard clients in real time.
    """

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self._connections.append(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            try:
                self._connections.remove(websocket)
            except ValueError:
                pass

    async def broadcast(self, message: dict) -> None:
        """
        Send a JSON message to all connected clients.
        Dead connections are silently removed.
        """
        dead: list[WebSocket] = []
        async with self._lock:
            connections = list(self._connections)

        for ws in connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    try:
                        self._connections.remove(ws)
                    except ValueError:
                        pass

    @property
    def active_connections(self) -> int:
        return len(self._connections)


# Module-level singleton used by main.py WebSocket endpoint and applicator
ws_manager = WebSocketManager()


class ApplicationAutomator:
    """
    Orchestrates automated job applications.

    Supports two modes:
    - "full_auto":  Runs the entire application without human intervention.
    - "copilot":    Pauses at review checkpoints and broadcasts status
                    updates via WebSocket for human oversight.
    """

    def __init__(
        self,
        mode: str,
        profile: dict,
        resumes: list[dict],
    ) -> None:
        if mode not in ("full_auto", "copilot"):
            raise ValueError(f"Invalid mode '{mode}'. Must be 'full_auto' or 'copilot'.")
        self.mode = mode
        self.profile = profile
        self.resumes = resumes

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_application(
        self,
        job_url: str,
        resume_label: str,
        job_data: dict,
        application_id: str,
    ) -> dict:
        """
        Execute a job application end-to-end.

        Args:
            job_url:        The URL of the job posting.
            resume_label:   Which resume to use (e.g. "Data Engineer").
            job_data:       Scraped job data from scraper.py.
            application_id: ID of the ApplicationRecord being processed.

        Returns:
            A result dict with keys: success (bool), status (str),
            answers_given (dict), error (optional str).
        """
        ats_platform = job_data.get("ats_platform") or detect_ats_platform(job_url)

        await self._broadcast_status(
            "starting",
            f"Starting {self.mode} application for {job_data.get('job_title', 'position')} "
            f"at {job_data.get('company', 'company')} via {ats_platform}",
            {"application_id": application_id, "ats_platform": ats_platform},
        )

        # Find the resume file path
        resume_file_path = self._get_resume_path(resume_label)
        if not resume_file_path:
            error_msg = f"Resume file for label '{resume_label}' not found."
            await self._broadcast_status("error", error_msg, {"application_id": application_id})
            return {"success": False, "status": "error", "answers_given": {}, "error": error_msg}

        handler = await self._get_handler(ats_platform)
        answers_given: dict = {}

        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=(self.mode == "full_auto"))
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                )
                page = await context.new_page()
                handler.page = page

                await self._broadcast_status(
                    "navigating",
                    f"Navigating to {job_url}",
                    {"application_id": application_id},
                )

                await page.goto(job_url, timeout=30000, wait_until="domcontentloaded")
                await handler.navigate_to_apply(page)

                await self._broadcast_status(
                    "filling",
                    "Filling application form fields",
                    {"application_id": application_id},
                )

                # Multi-step form loop
                page_number = 1
                while True:
                    fields = await handler.get_form_fields(page)
                    await self._broadcast_status(
                        "page_fields",
                        f"Page {page_number}: found {len(fields)} fields",
                        {"application_id": application_id, "field_count": len(fields)},
                    )

                    # Upload resume if a file field is present
                    file_fields = [f for f in fields if f.field_type == "file"]
                    if file_fields:
                        await handler.upload_resume(page, resume_file_path)
                        await self._broadcast_status(
                            "resume_uploaded",
                            "Resume uploaded",
                            {"application_id": application_id},
                        )

                    # Fill text/select/textarea fields via FieldMapper
                    from utils.field_mapper import FieldMapper
                    from services.question_answerer import (
                        answer_question,
                        build_profile_summary,
                    )

                    mapper = FieldMapper(self.profile)
                    profile_summary = build_profile_summary(self.profile)
                    resume_text = self._get_resume_text(resume_label)

                    for field in fields:
                        if field.field_type == "file" or field.filled:
                            continue

                        value, confidence = mapper.map_field(field)

                        # Low confidence — ask Claude for help
                        if value is None or confidence < 0.6:
                            if field.label and len(field.label) > 3:
                                value = await answer_question(
                                    question=field.label,
                                    job_title=job_data.get("job_title", ""),
                                    company=job_data.get("company", ""),
                                    job_description=job_data.get("job_description", ""),
                                    resume_text=resume_text,
                                    profile_summary=profile_summary,
                                )
                                field.needs_review = True

                        if value:
                            await handler.fill_field(page, field, value)
                            answers_given[field.label or field.name] = value

                    # In copilot mode, pause for human review
                    if self.mode == "copilot":
                        await self._broadcast_status(
                            "review_requested",
                            f"Page {page_number} filled — please review before continuing.",
                            {
                                "application_id": application_id,
                                "page_number": page_number,
                                "answers": answers_given,
                            },
                        )

                    has_next = await handler.next_page(page)
                    if not has_next:
                        break
                    page_number += 1

                # Submit
                await self._broadcast_status(
                    "submitting",
                    "Submitting application",
                    {"application_id": application_id},
                )
                submitted = await handler.submit(page)

                await context.close()
                await browser.close()

            status = "submitted" if submitted else "submission_failed"
            await self._broadcast_status(
                status,
                "Application submitted successfully." if submitted else "Submission failed.",
                {"application_id": application_id},
            )
            return {
                "success": submitted,
                "status": status,
                "answers_given": answers_given,
            }

        except NotImplementedError as exc:
            error_msg = str(exc)
            await self._broadcast_status("error", error_msg, {"application_id": application_id})
            return {"success": False, "status": "not_implemented", "answers_given": {}, "error": error_msg}
        except Exception as exc:
            error_msg = f"Automation error: {exc}"
            await self._broadcast_status("error", error_msg, {"application_id": application_id})
            return {"success": False, "status": "error", "answers_given": {}, "error": error_msg}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_handler(self, ats_platform: str) -> ATSHandler:
        """Return the correct ATSHandler subclass for the detected platform."""
        platform_lower = ats_platform.lower()

        if "workday" in platform_lower:
            return WorkdayHandler(profile=self.profile, mode=self.mode)
        if "greenhouse" in platform_lower:
            return GreenhouseHandler(profile=self.profile, mode=self.mode)
        if "lever" in platform_lower:
            return LeverHandler(profile=self.profile, mode=self.mode)

        # Default: generic fuzzy-matching handler
        return GenericHandler(profile=self.profile, mode=self.mode)

    async def _broadcast_status(
        self,
        status: str,
        message: str,
        data: Optional[dict] = None,
    ) -> None:
        """Broadcast a status update via the global WebSocketManager."""
        payload: dict = {"status": status, "message": message}
        if data:
            payload.update(data)
        await ws_manager.broadcast(payload)

    def _get_resume_path(self, resume_label: str) -> Optional[str]:
        """Find the local file path for the given resume label."""
        import os

        file_name = resume_label.replace(" ", "_") + ".pdf"
        base_dir = "/home/user/QuickApply/resumes"
        full_path = os.path.join(base_dir, file_name)
        return full_path if os.path.exists(full_path) else None

    def _get_resume_text(self, resume_label: str) -> str:
        """Return the parsed text for a resume by label."""
        for resume in self.resumes:
            if resume.get("label") == resume_label:
                return resume.get("parsed_text", "") or ""
        return ""
