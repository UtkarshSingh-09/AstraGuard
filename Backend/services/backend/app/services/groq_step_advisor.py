from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib import error, request

from app.core.config import settings


class GroqStepAdvisor:
    def _enabled(self) -> bool:
        return bool(settings.groq_api_key and settings.groq_model)

    async def suggest_next_step(
        self,
        *,
        portal: str,
        goal: str,
        current_url: str,
        page_title: str,
        last_error: str,
        evidence_steps: list[str] | None = None,
    ) -> dict[str, Any]:
        fallback = self._fallback(portal=portal, goal=goal, last_error=last_error, current_url=current_url)
        if not self._enabled():
            return fallback

        prompt = self._build_prompt(
            portal=portal,
            goal=goal,
            current_url=current_url,
            page_title=page_title,
            last_error=last_error,
            evidence_steps=evidence_steps or [],
        )
        try:
            raw = await asyncio.to_thread(self._call_groq, prompt)
            parsed = self._parse(raw)
            if parsed:
                parsed["source"] = "groq"
                return parsed
        except Exception:
            pass
        return fallback

    def _call_groq(self, prompt: str) -> str:
        payload = {
            "model": settings.groq_model,
            "temperature": 0.1,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a fintech workflow assistant. Respond ONLY JSON "
                        "with keys: instruction, step_type, needs_user_input, confidence, reason."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        }
        req = request.Request(
            url=f"{settings.groq_base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.groq_api_key}",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=settings.groq_timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Groq HTTP {exc.code}: {body[:240]}") from exc
        except Exception as exc:
            raise RuntimeError(f"Groq call failed: {exc}") from exc
        return data["choices"][0]["message"]["content"]

    @staticmethod
    def _parse(raw: str) -> dict[str, Any] | None:
        text = (raw or "").strip()
        if not text:
            return None
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()
        try:
            obj = json.loads(text)
        except Exception:
            return None
        instruction = str(obj.get("instruction", "")).strip()
        if not instruction:
            return None
        return {
            "instruction": instruction,
            "step_type": str(obj.get("step_type", "manual")),
            "needs_user_input": bool(obj.get("needs_user_input", True)),
            "confidence": float(obj.get("confidence", 0.5)),
            "reason": str(obj.get("reason", "Model-guided fallback step")),
        }

    @staticmethod
    def _build_prompt(
        *,
        portal: str,
        goal: str,
        current_url: str,
        page_title: str,
        last_error: str,
        evidence_steps: list[str],
    ) -> str:
        compact_steps = "\n".join(f"- {s}" for s in evidence_steps[-8:]) or "- none"
        return (
            f"Portal: {portal}\n"
            f"Goal: {goal}\n"
            f"Current URL: {current_url}\n"
            f"Page title: {page_title}\n"
            f"Last error: {last_error}\n"
            f"Recent execution steps:\n{compact_steps}\n\n"
            "Return one concrete NEXT action for user in <= 20 words.\n"
            "Use step_type as one of: navigate, input, otp, captcha, upload, retry, contact_support.\n"
            "Return JSON only."
        )

    @staticmethod
    def _fallback(*, portal: str, goal: str, last_error: str, current_url: str) -> dict[str, Any]:
        if portal == "cams":
            instruction = "Open CAMS CAS page, submit PAN+email request manually, then upload received CAS PDF."
            step_type = "upload"
        else:
            instruction = "Complete login/OTP on portal, download Form16 PDF, then upload it in AstraGuard."
            step_type = "otp"
        return {
            "instruction": instruction,
            "step_type": step_type,
            "needs_user_input": True,
            "confidence": 0.42,
            "reason": f"Fallback guidance due to: {last_error or 'automation uncertainty'}",
            "context": {"portal": portal, "goal": goal, "url": current_url},
            "source": "fallback",
        }


groq_step_advisor = GroqStepAdvisor()
