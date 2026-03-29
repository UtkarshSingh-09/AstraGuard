from __future__ import annotations

import asyncio
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.models.contracts import JobStatus
from app.pipelines.document_monitor import DocumentMonitor
from app.services.cas_provider import cas_provider_client
from app.services.groq_step_advisor import groq_step_advisor
from app.services.job_registry import job_service
from app.services.mailbox_ingestion import save_attachment_file, wait_for_cams_pdf_from_mailbox
from app.services.secret_store import secret_store


class CAMSAgent:
    """
    Background CAMS fetch agent.
    Mode:
    - real: attempts browser automation if playwright is available and selectors work
    - mock: deterministic fallback for demo reliability
    """

    async def run(self, job_id: str, payload: dict[str, Any]) -> None:
        mode = payload.get("mode", "mock")
        try:
            job_service.update_job(job_id, status=JobStatus.RUNNING, message="CAMS agent started")
            if mode == "mock":
                await self._run_mock(job_id)
                return
            await self._run_real(job_id, payload)
        except Exception as exc:
            job_service.update_job(
                job_id,
                status=JobStatus.FAILED,
                message=f"CAMS agent failed: {exc}",
                error={
                    "code": "cams_fetch_failed",
                    "message": str(exc),
                    "traceback": traceback.format_exc(limit=12),
                },
            )
        finally:
            job = job_service.get_job(job_id)
            if not job or job.status != JobStatus.AWAITING_USER_STEP:
                secret_store.delete(job_id)

    async def _run_mock(self, job_id: str) -> None:
        await asyncio.sleep(0.5)
        job_service.update_job(job_id, status=JobStatus.DOWNLOADED, message="Mock CAS downloaded")
        await asyncio.sleep(0.5)
        job_service.update_job(
            job_id,
            status=JobStatus.COMPLETE,
            message="Mock CAS parsed successfully",
            result={
                "status": "complete",
                "source": "mock_cams",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "document_type": "cams_statement",
            },
        )

    async def _run_real(self, job_id: str, payload: dict[str, Any]) -> None:
        secret = secret_store.get(job_id) or {}
        pan = secret.get("pan")
        email = secret.get("email")
        if not pan or not email:
            raise ValueError("Missing PAN/email secret for CAMS fetch")

        job_service.update_job(job_id, status=JobStatus.RUNNING, message="Submitting CAMS mailback request")
        evidence: dict[str, Any] = {"visited_url": "", "screenshots": [], "steps": []}

        provider_mode = self._normalize_provider_mode(payload.get("provider_mode"))
        priority = self._resolve_priority(payload.get("priority"))
        if "provider_api" in priority and provider_mode != "playwright_only":
            provider_result = await cas_provider_client.request_statement(
                user_id=payload.get("user_id", "unknown"),
                pan=pan,
                email=email,
                from_date=payload.get("from_date"),
                to_date=payload.get("to_date"),
            )
            if provider_result.ok:
                job_service.update_job(
                    job_id,
                    status=JobStatus.COMPLETE,
                    message="CAS fetched via provider API",
                    result={
                        "status": "complete",
                        "source": "provider_api",
                        "provider": payload.get("provider_name", "cas_provider"),
                        "document_type": "cams_statement",
                        "provider_payload": provider_result.payload or {},
                        "evidence": {"steps": ["provider_api:success"]},
                    },
                )
                return

            evidence["steps"].append(
                f"provider_api:failed code={provider_result.code} message={provider_result.message}"
            )
            if provider_mode == "provider_only":
                job_service.update_job(
                    job_id,
                    status=JobStatus.COMPLETE,
                    message="Provider-only mode failed; no Playwright fallback allowed",
                    result={
                        "status": "degraded_mode",
                        "source": "provider_api",
                        "provider_status": provider_result.code,
                        "next_step": "Switch provider_mode to auto or upload CAS PDF",
                        "evidence": evidence,
                    },
                    error={
                        "code": provider_result.code,
                        "message": provider_result.message,
                    },
                )
                return

        if provider_mode == "provider_only":
            job_service.update_job(
                job_id,
                status=JobStatus.COMPLETE,
                message="Provider-only mode selected; Playwright fallback disabled",
                result={
                    "status": "degraded_mode",
                    "source": "provider_api",
                    "next_step": "Configure provider integration or switch provider_mode to auto",
                    "evidence": evidence,
                },
            )
            return

        try:
            from playwright.async_api import async_playwright  # type: ignore
        except Exception as exc:
            ai_next_step = await groq_step_advisor.suggest_next_step(
                portal="cams",
                goal="Request CAMS consolidated account statement",
                current_url=cams_url,
                page_title="playwright_unavailable",
                last_error=str(exc),
                evidence_steps=evidence.get("steps", []),
            )
            job_service.update_job(
                job_id,
                status=JobStatus.COMPLETE,
                message="Playwright unavailable - switched to assisted fallback",
                result={
                    "status": "degraded_mode",
                    "source": "cams_agent",
                    "next_step": "Install Playwright for real browser automation or continue with manual CAS upload",
                    "required_action": "install_playwright_or_upload",
                    "error_hint": str(exc),
                    "ai_next_step": ai_next_step,
                },
            )
            return

        default_cams_url = "https://www.camsonline.com/Investors/MailbackServices"
        candidate_urls = [
            default_cams_url,
            "https://www.camsonline.com/Investors/Statements",
            "https://www.camsonline.com/Investors",
            "https://www.camsonline.com/Investors/Statements/Consolidated-Account-Statement",
            "https://www.camsonline.com/Investors/Statements/CAS-CAMS",
        ]
        raw_cams_url = payload.get("cams_url")
        cams_url = raw_cams_url.strip() if isinstance(raw_cams_url, str) else ""
        if not cams_url:
            cams_url = default_cams_url
        if not cams_url.lower().startswith(("http://", "https://")):
            cams_url = f"https://{cams_url}"
        if cams_url not in candidate_urls:
            candidate_urls.insert(0, cams_url)
        artifacts_dir = Path("artifacts/ingestion")
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        evidence["visited_url"] = cams_url
        max_attempts = int(payload.get("max_attempts", 3))
        last_error = ""
        for attempt in range(1, max_attempts + 1):
            try:
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    context = await browser.new_context(viewport={"width": 1440, "height": 2200})
                    page = await context.new_page()
                    current_try_url = candidate_urls[(attempt - 1) % len(candidate_urls)]
                    await self._safe_goto(page, current_try_url, timeout=90000)
                    await self._clear_disclaimer_modals(page)
                    await self._dismiss_common_overlays(page)
                    await self._ensure_cas_form_visible(page)
                    await self._clear_disclaimer_modals(page)
                    evidence["steps"].append(f"attempt_{attempt}: page_loaded")
                    evidence["steps"].append(f"attempt_{attempt}: current_url={page.url}")
                    loaded_ss = artifacts_dir / f"{job_id}_attempt{attempt}_loaded.png"
                    await page.screenshot(path=str(loaded_ss), full_page=True)
                    evidence["screenshots"].append(f"/artifacts/ingestion/{loaded_ss.name}")
                    html_dump = artifacts_dir / f"{job_id}_attempt{attempt}_loaded.html"
                    html_dump.write_text(await page.content(), encoding="utf-8")
                    evidence["steps"].append(f"attempt_{attempt}: html_dump={html_dump.name}")
                    if not await self._has_form_markers(page):
                        title = await page.title()
                        evidence["steps"].append(
                            f"attempt_{attempt}: form_markers_missing title={title} url={page.url}"
                        )
                        raise RuntimeError("PAN/email form markers not visible after navigation flow")

                    await self._fill_pan(page, pan)
                    evidence["steps"].append(f"attempt_{attempt}: pan_filled")
                    await self._fill_email(page, email)
                    evidence["steps"].append(f"attempt_{attempt}: email_filled")
                    if payload.get("from_date"):
                        await self._fill_optional_date(page, payload["from_date"], kind="from")
                    if payload.get("to_date"):
                        await self._fill_optional_date(page, payload["to_date"], kind="to")
                    await self._click_submit(page)
                    evidence["steps"].append(f"attempt_{attempt}: submit_clicked")
                    submitted_ss = artifacts_dir / f"{job_id}_attempt{attempt}_submitted.png"
                    await page.screenshot(path=str(submitted_ss), full_page=True)
                    evidence["screenshots"].append(f"/artifacts/ingestion/{submitted_ss.name}")
                    submitted_html = artifacts_dir / f"{job_id}_attempt{attempt}_submitted.html"
                    submitted_html.write_text(await page.content(), encoding="utf-8")
                    evidence["steps"].append(f"attempt_{attempt}: submitted_html_dump={submitted_html.name}")

                    # Soft confirmation heuristics
                    content = (await page.content()).lower()
                    if any(k in content for k in ["captcha", "i am not a robot", "verification code"]):
                        challenge_ss = artifacts_dir / f"{job_id}_attempt{attempt}_challenge.png"
                        await page.screenshot(path=str(challenge_ss), full_page=True)
                        evidence["screenshots"].append(f"/artifacts/ingestion/{challenge_ss.name}")
                        evidence["steps"].append(f"attempt_{attempt}: challenge_detected")
                        ai_next_step = await groq_step_advisor.suggest_next_step(
                            portal="cams",
                            goal="Complete CAMS verification challenge and continue CAS request",
                            current_url=page.url or cams_url,
                            page_title=await page.title(),
                            last_error="verification challenge detected",
                            evidence_steps=evidence.get("steps", []),
                        )
                        job_service.update_job(
                            job_id,
                            status=JobStatus.AWAITING_USER_STEP,
                            message="CAMS portal requested verification. Complete challenge manually and re-run.",
                            result={
                                "status": "awaiting_manual_verification",
                                "source": "cams_mailback",
                                "evidence": evidence,
                                "ai_next_step": ai_next_step,
                            },
                        )
                        await context.close()
                        await browser.close()
                        return

                    await asyncio.sleep(2)
                    authenticity = await self._assess_submission_authenticity(page)
                    evidence["steps"].append(
                        f"attempt_{attempt}: authenticity={authenticity['status']} reason={authenticity['reason']}"
                    )
                    await context.close()
                    await browser.close()
                    evidence["steps"].append(f"attempt_{attempt}: request_submission_checked")
                    if authenticity["status"] == "confirmed":
                        job_service.update_job(
                            job_id,
                            status=JobStatus.RUNNING,
                            message="CAMS request accepted by portal. Waiting for statement delivery.",
                            result={
                                "status": "processing",
                                "source": "cams_mailback",
                                "attempt": attempt,
                                "authenticity": authenticity,
                                "evidence": evidence,
                                "next_step": "Upload received CAS PDF or connect mailbox ingestion",
                            },
                            error=None,
                        )
                    else:
                        ai_next_step = await groq_step_advisor.suggest_next_step(
                            portal="cams",
                            goal="Confirm CAMS CAS request and continue",
                            current_url=page.url or cams_url,
                            page_title=await page.title(),
                            last_error=authenticity["reason"],
                            evidence_steps=evidence.get("steps", []),
                        )
                        job_service.update_job(
                            job_id,
                            status=JobStatus.AWAITING_USER_STEP,
                            message="Portal did not return verifiable CAS submission confirmation.",
                            result={
                                "status": "awaiting_user_step",
                                "source": "assisted_playwright",
                                "attempt": attempt,
                                "required_step": "manual_confirmation_or_upload",
                                "authenticity": authenticity,
                                "assist_links": [
                                    "https://www.camsonline.com/Investors/Statements/Consolidated-Account-Statement",
                                    "https://www.camsonline.com/Investors/Statements/CAS-CAMS",
                                ],
                                "instruction": (
                                    "Portal response did not confirm request deterministically. "
                                    "Please complete request manually and upload CAS PDF."
                                ),
                                "evidence": evidence,
                                "ai_next_step": ai_next_step,
                            },
                            error={
                                "code": "cams_authenticity_unverified",
                                "message": authenticity["reason"],
                            },
                        )
                        return
                    await self._maybe_auto_ingest_mailbox(job_id, payload, secret, evidence)
                    return
            except Exception as exc:
                last_error = str(exc)
                job_service.update_job(
                    job_id,
                    status=JobStatus.RUNNING,
                    message=f"CAMS attempt {attempt}/{max_attempts} failed, retrying",
                    error={"code": "cams_attempt_failed", "message": last_error},
                )
                await asyncio.sleep(min(2 * attempt, 8))

        ai_next_step = await groq_step_advisor.suggest_next_step(
            portal="cams",
            goal="Reach CAMS CAS request form and submit PAN+email",
            current_url=evidence.get("visited_url", ""),
            page_title="form_markers_missing",
            last_error=last_error,
            evidence_steps=evidence.get("steps", []),
        )
        job_service.update_job(
            job_id,
            status=JobStatus.AWAITING_USER_STEP,
            message="Automation could not reach CAS form. Assisted step required.",
            result={
                "status": "awaiting_user_step",
                "source": "assisted_playwright",
                "required_step": "manual_navigation_or_upload",
                "assist_links": [
                    "https://www.camsonline.com/Investors/Statements/Consolidated-Account-Statement",
                    "https://www.camsonline.com/Investors/Statements/CAS-CAMS",
                ],
                "instruction": (
                    "Open one assist link, complete CAS request manually, then upload received CAS PDF "
                    "or continue with mailbox auto-ingest path."
                ),
                "continue_endpoint": f"/api/jobs/{job_id}/user-step",
                "evidence": evidence,
                "last_error": last_error,
                "ai_next_step": ai_next_step,
            },
            error={"code": "cams_manual_assist_required", "message": last_error},
        )
        return

    @staticmethod
    def _normalize_provider_mode(raw: Any) -> str:
        value = str(raw or "auto").strip().lower()
        if value not in {"auto", "provider_only", "playwright_only"}:
            return "auto"
        return value

    @staticmethod
    def _resolve_priority(raw: Any) -> list[str]:
        default = ["provider_api", "assisted_playwright", "upload_fallback"]
        if not isinstance(raw, list) or not raw:
            return default
        normalized = [str(x).strip().lower() for x in raw if str(x).strip()]
        return normalized or default

    @staticmethod
    async def _safe_goto(target, url: str, *, timeout: int = 90000) -> None:
        if not isinstance(url, str) or not url.strip():
            raise ValueError("Invalid CAMS URL provided for navigation")
        goto_fn = getattr(target, "goto", None)
        if goto_fn is None:
            raise RuntimeError("Playwright target has no goto() method")
        try:
            await goto_fn(url=url, timeout=timeout)
            return
        except TypeError:
            pass
        try:
            await goto_fn(url, timeout=timeout)
            return
        except TypeError:
            cls = type(target)
            class_goto = getattr(cls, "goto", None)
            if class_goto is None:
                raise
            bound_goto = class_goto.__get__(target, cls)
            await bound_goto(url, timeout=timeout)

    async def _maybe_auto_ingest_mailbox(
        self,
        job_id: str,
        payload: dict[str, Any],
        secret: dict[str, Any],
        evidence: dict[str, Any],
    ) -> None:
        if not payload.get("auto_ingest_mailbox"):
            return
        app_password = secret.get("mailbox_app_password")
        if not app_password:
            job_service.update_job(
                job_id,
                status=JobStatus.AWAITING_USER_STEP,
                message="CAMS submitted, mailbox auto-ingest skipped (missing app password)",
                result={
                    "status": "awaiting_user_step",
                    "source": "cams_mailback",
                    "evidence": evidence,
                    "next_step": "Provide mailbox app password or upload received CAS PDF",
                },
            )
            return

        job_service.update_job(job_id, status=JobStatus.RUNNING, message="Waiting for CAS PDF in mailbox")
        attachment = await wait_for_cams_pdf_from_mailbox(
            email_address=secret["email"],
            app_password=app_password,
            imap_host=payload.get("imap_host", "imap.gmail.com"),
            imap_port=int(payload.get("imap_port", 993)),
            timeout_seconds=int(payload.get("mailbox_timeout_seconds", 180)),
            poll_interval_seconds=int(payload.get("mailbox_poll_interval_seconds", 20)),
        )
        if not attachment:
            job_service.update_job(
                job_id,
                status=JobStatus.AWAITING_USER_STEP,
                message="CAS email not found within timeout window",
                result={
                    "status": "awaiting_user_step",
                    "source": "cams_mailback",
                    "evidence": evidence,
                    "next_step": "Upload CAS PDF manually",
                },
            )
            return

        saved_path = save_attachment_file(
            filename=attachment["filename"],
            content=attachment["content"],
            prefix="cams",
        )
        monitor = DocumentMonitor()
        validation = monitor.validate(saved_path, expected_type="cams_statement", extracted_text="")
        if not validation.accepted:
            job_service.update_job(
                job_id,
                status=JobStatus.FAILED,
                message=f"Downloaded CAS failed validation: {validation.reason}",
                error={"code": "invalid_cams_document", "message": validation.reason},
            )
            return

        job_service.update_job(
            job_id,
            status=JobStatus.COMPLETE,
            message="CAMS CAS auto-ingested and attached",
            result={
                "status": "complete",
                "source": "cams_mailback_auto_ingest",
                "document_type": "cams_statement",
                "evidence": evidence,
                "attachment": {
                    "path": saved_path,
                    "filename": attachment["filename"],
                    "confidence": validation.confidence,
                },
                "upload_payload": {
                    "mode": "uploaded_file",
                    "file_path": saved_path,
                    "document_type": "cams_statement",
                },
            },
        )

    @staticmethod
    async def _assess_submission_authenticity(page) -> dict[str, str | list[str]]:
        body = (await page.content()).lower()
        url = (page.url or "").lower()
        title = (await page.title()).lower()

        success_markers = [
            "statement will be sent",
            "mail has been sent",
            "request submitted",
            "request accepted",
            "successfully submitted",
            "cas request",
            "acknowledgement",
        ]
        failure_markers = [
            "invalid pan",
            "invalid email",
            "no records found",
            "error occurred",
            "please try again",
            "unable to process",
        ]
        matched_success = [m for m in success_markers if m in body or m in title]
        matched_failure = [m for m in failure_markers if m in body or m in title]

        if matched_failure:
            return {
                "status": "rejected",
                "reason": f"Portal indicates request rejection: {', '.join(matched_failure)}",
                "url": url,
                "success_markers": matched_success,
                "failure_markers": matched_failure,
            }

        # Require at least one deterministic success marker for autonomous authenticity.
        if matched_success:
            return {
                "status": "confirmed",
                "reason": "Portal success marker detected",
                "url": url,
                "success_markers": matched_success,
                "failure_markers": matched_failure,
            }

        return {
            "status": "unverified",
            "reason": "No deterministic success marker found after submit",
            "url": url,
            "success_markers": matched_success,
            "failure_markers": matched_failure,
        }

    @staticmethod
    async def _fill_pan(page, pan: str) -> None:
        for target in CAMSAgent._iter_targets(page):
            try:
                await CAMSAgent._fill_pan_on_target(target, pan)
                return
            except Exception:
                continue
        raise RuntimeError("Could not find editable input for markers: ['pan']")

    @staticmethod
    async def _fill_pan_on_target(target, pan: str) -> None:
        pan_selectors = [
            "input[name*='pan' i]",
            "input[id*='pan' i]",
            "input[placeholder*='PAN' i]",
            "input[aria-label*='PAN' i]",
        ]
        for selector in pan_selectors:
            loc = target.locator(selector).first
            if await loc.count():
                await CAMSAgent._fill_if_editable(loc, pan)
                return
        try:
            await CAMSAgent._fill_input_by_attr_contains(target, ["pan", "permanent account"], pan)
            return
        except Exception:
            pass
        # Heuristic fallback: visible short text-like input (PAN is usually 10 chars)
        inputs = target.locator("input[type='text'], input:not([type])")
        count = await inputs.count()
        for i in range(count):
            cand = inputs.nth(i)
            try:
                if not await cand.is_visible() or not await cand.is_enabled():
                    continue
                maxlength = await cand.get_attribute("maxlength")
                if maxlength and maxlength.isdigit() and 8 <= int(maxlength) <= 12:
                    await CAMSAgent._fill_if_editable(cand, pan)
                    return
            except Exception:
                continue
        raise RuntimeError("Could not find editable input for markers: ['pan']")

    @staticmethod
    async def _fill_email(page, email: str) -> None:
        for target in CAMSAgent._iter_targets(page):
            try:
                await CAMSAgent._fill_email_on_target(target, email)
                return
            except Exception:
                continue
        raise RuntimeError("Could not find editable input for markers: ['email', 'mail']")

    @staticmethod
    async def _fill_email_on_target(target, email: str) -> None:
        email_selectors = [
            "input[type='email']",
            "input[name*='email' i]",
            "input[id*='email' i]",
            "input[placeholder*='email' i]",
            "input[aria-label*='email' i]",
        ]
        for selector in email_selectors:
            loc = target.locator(selector).first
            if await loc.count():
                await CAMSAgent._fill_if_editable(loc, email)
                return
        try:
            await CAMSAgent._fill_input_by_attr_contains(target, ["email", "mail"], email)
            return
        except Exception:
            pass
        # Heuristic fallback: visible text-like input containing email hints
        inputs = target.locator("input[type='text'], input:not([type])")
        count = await inputs.count()
        for i in range(count):
            cand = inputs.nth(i)
            try:
                if not await cand.is_visible() or not await cand.is_enabled():
                    continue
                attrs = " ".join(
                    [
                        await cand.get_attribute("name") or "",
                        await cand.get_attribute("id") or "",
                        await cand.get_attribute("placeholder") or "",
                        await cand.get_attribute("aria-label") or "",
                    ]
                ).lower()
                if "mail" in attrs:
                    await CAMSAgent._fill_if_editable(cand, email)
                    return
            except Exception:
                continue
        raise RuntimeError("Could not find editable input for markers: ['email', 'mail']")

    @staticmethod
    async def _fill_optional_date(page, value: str, *, kind: str) -> None:
        for target in CAMSAgent._iter_targets(page):
            if await CAMSAgent._fill_optional_date_on_target(target, value, kind=kind):
                return

    @staticmethod
    async def _fill_optional_date_on_target(target, value: str, *, kind: str) -> bool:
        selectors = [
            f"input[name*='{kind}' i]",
            f"input[id*='{kind}' i]",
            f"input[placeholder*='{kind}' i]",
        ]
        for selector in selectors:
            loc = target.locator(selector).first
            if await loc.count():
                await loc.fill(value)
                return True
        return False

    @staticmethod
    async def _fill_if_editable(locator, value: str) -> None:
        el_type = (await locator.get_attribute("type") or "").lower()
        if el_type in {"hidden", "button", "submit", "checkbox", "radio"}:
            raise RuntimeError(f"Matched non-editable input type: {el_type}")
        await locator.fill(value)

    @staticmethod
    async def _fill_input_by_attr_contains(page, needles: list[str], value: str) -> None:
        inputs = page.locator("input, textarea")
        count = await inputs.count()
        for idx in range(count):
            candidate = inputs.nth(idx)
            try:
                if not await candidate.is_visible():
                    continue
                if not await candidate.is_enabled():
                    continue
                attrs = [
                    await candidate.get_attribute("name") or "",
                    await candidate.get_attribute("id") or "",
                    await candidate.get_attribute("placeholder") or "",
                    await candidate.get_attribute("aria-label") or "",
                    await candidate.get_attribute("type") or "",
                ]
                hay = " ".join(attrs).lower()
                if any(n in hay for n in needles):
                    await CAMSAgent._fill_if_editable(candidate, value)
                    return
            except Exception:
                continue
        raise RuntimeError(f"Could not find editable input for markers: {needles}")

    @staticmethod
    async def _click_submit(page) -> None:
        for target in CAMSAgent._iter_targets(page):
            try:
                await CAMSAgent._click_submit_on_target(target)
                return
            except Exception:
                continue
        raise RuntimeError("Could not find submit button in page/frames")

    @staticmethod
    async def _click_submit_on_target(target) -> None:
        submit_selectors = [
            "button[type='submit']",
            "input[type='submit']",
            "button:has-text('Submit')",
            "button:has-text('Send')",
            "button:has-text('Generate')",
        ]
        for selector in submit_selectors:
            loc = target.locator(selector).first
            if await loc.count():
                await loc.click()
                return
        await target.get_by_role("button", name="Submit", exact=False).click()

    @staticmethod
    def _iter_targets(page) -> list:
        targets = [page]
        try:
            targets.extend(list(page.frames))
        except Exception:
            pass
        return targets

    @staticmethod
    async def _dismiss_common_overlays(page) -> None:
        dismiss_texts = ["Accept", "I Agree", "Got it", "Close", "OK"]
        for text in dismiss_texts:
            try:
                btn = page.get_by_role("button", name=text, exact=False).first
                if await btn.count():
                    await btn.click(timeout=1200)
                    await asyncio.sleep(0.2)
            except Exception:
                continue

    @staticmethod
    async def _clear_disclaimer_modals(page, *, max_rounds: int = 5) -> None:
        for _ in range(max_rounds):
            modals = page.locator("mat-dialog-container")
            modal_count = await modals.count()
            if modal_count == 0:
                return
            progressed = False
            for i in range(modal_count):
                modal = modals.nth(i)
                try:
                    modal_text = (await modal.inner_text()).lower()
                    if "disclaimer" not in modal_text:
                        continue

                    # Select ACCEPT radio if present (use force as angular radio inputs can be visually hidden)
                    accept_radio = modal.locator("input[type='radio'][value='ACCEPT']").first
                    if await accept_radio.count():
                        await accept_radio.check(force=True)
                        progressed = True
                        await asyncio.sleep(0.15)
                    else:
                        accept_label = modal.get_by_text("ACCEPT", exact=False).first
                        if await accept_label.count():
                            await accept_label.click(timeout=2000, force=True)
                            progressed = True
                            await asyncio.sleep(0.15)

                    # Click PROCEED
                    proceed_input = modal.locator("input[type='button'][value*='PROCEED' i]").first
                    if await proceed_input.count():
                        await proceed_input.click(timeout=2500, force=True)
                        progressed = True
                        await asyncio.sleep(0.5)
                        continue
                    proceed_btn = modal.get_by_role("button", name="PROCEED", exact=False).first
                    if await proceed_btn.count():
                        await proceed_btn.click(timeout=2500, force=True)
                        progressed = True
                        await asyncio.sleep(0.5)
                except Exception:
                    continue
            if not progressed:
                return
            await asyncio.sleep(0.6)

    @staticmethod
    async def _ensure_cas_form_visible(page) -> None:
        if await CAMSAgent._has_form_markers(page):
            return
        direct_cas_paths = [
            "https://www.camsonline.com/Investors/Statements/Consolidated-Account-Statement",
            "https://www.camsonline.com/Investors/Statements/CAS-CAMS",
        ]
        for url in direct_cas_paths:
            try:
                await CAMSAgent._safe_goto(page, url, timeout=90000)
                await CAMSAgent._clear_disclaimer_modals(page)
                if await CAMSAgent._has_form_markers(page):
                    return
            except Exception:
                continue

        nav_clicks = [
            ("text", "CAS - CAMS+KFintech"),
            ("text", "CAS - CAMS + KFintech"),
            ("text", "CAMS+KFintech"),
            ("link", "MF Investors"),
            ("link", "Statements"),
            ("link", "CAS"),
            ("link", "Consolidated Account Statement"),
            ("link", "CAMS+KFintech"),
            ("link", "Mailback"),
            ("link", "Mailback Services"),
            ("link", "Request Statement"),
            ("button", "MF Investors"),
            ("button", "Statements"),
            ("button", "CAS"),
            ("button", "Mailback"),
            ("button", "Mailback Services"),
        ]
        for role, name in nav_clicks:
            try:
                if role == "text":
                    element = page.get_by_text(name, exact=False).first
                else:
                    element = page.get_by_role(role, name=name, exact=False).first
                if await element.count():
                    await element.click(timeout=2500)
                    await asyncio.sleep(1.0)
                    await CAMSAgent._clear_disclaimer_modals(page)
                    if await CAMSAgent._has_form_markers(page):
                        return
            except Exception:
                continue

        # Last attempt: read discovered href and navigate explicitly if available
        try:
            route_link = page.locator("a[href*='Consolidated-Account-Statement']").first
            if await route_link.count():
                href = await route_link.get_attribute("href")
                if href:
                    if href.startswith("/"):
                        href = f"https://www.camsonline.com{href}"
                    await CAMSAgent._safe_goto(page, href, timeout=90000)
                    await CAMSAgent._clear_disclaimer_modals(page)
        except Exception:
            return

    @staticmethod
    async def _has_form_markers(page) -> bool:
        has_pan = False
        has_email = False
        for target in CAMSAgent._iter_targets(page):
            try:
                pan_candidates = target.locator(
                    "input[name*='pan' i], input[id*='pan' i], input[placeholder*='pan' i], input[aria-label*='pan' i]"
                )
                email_candidates = target.locator(
                    "input[type='email'], input[name*='email' i], input[id*='email' i], input[placeholder*='email' i], input[aria-label*='email' i]"
                )
                if await pan_candidates.count():
                    has_pan = True
                if await email_candidates.count():
                    has_email = True
                if has_pan and has_email:
                    return True
            except Exception:
                continue
        return has_pan and has_email
