"""
Centralized Groq LLM client with model routing, retry logic, and rate limiting.

Model routing strategy:
  - FAST (llama3-8b-8192):   intent detection, classification, compliance checks
  - QUALITY (llama-3.3-70b-versatile): narration, explanations, messages
"""

from __future__ import annotations

import os
import time
import logging
from functools import lru_cache

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

load_dotenv()

logger = logging.getLogger("astraguard.groq")

# ─── Constants ────────────────────────────────────────────────────────────────

FAST_MODEL = "llama-3.1-8b-instant"
QUALITY_MODEL = "llama-3.3-70b-versatile"
MAX_RPM = 30  # Groq free tier limit


# ─── Simple Token Bucket Rate Limiter ─────────────────────────────────────────

class RateLimiter:
    """Simple token-bucket rate limiter for Groq API calls."""

    def __init__(self, max_calls: int = MAX_RPM, window_seconds: int = 60):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._calls: list[float] = []

    def wait_if_needed(self):
        """Block until a request slot is available."""
        now = time.time()
        # Remove calls outside the window
        self._calls = [t for t in self._calls if now - t < self.window_seconds]

        if len(self._calls) >= self.max_calls:
            sleep_time = self._calls[0] + self.window_seconds - now + 0.1
            logger.warning(f"Rate limit reached. Sleeping {sleep_time:.1f}s...")
            time.sleep(max(sleep_time, 0.1))

        self._calls.append(time.time())


_rate_limiter = RateLimiter()


# ─── LLM Factory ──────────────────────────────────────────────────────────────

def _get_api_key() -> str:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise ValueError(
            "GROQ_API_KEY not found in environment. "
            "Set it in .env or export it."
        )
    return key


@lru_cache(maxsize=2)
def get_fast_llm() -> ChatGroq:
    """
    Returns llama3-8b-8192 — use for:
    - Intent detection
    - DNA extraction
    - Compliance classification
    - Life event detection
    """
    return ChatGroq(
        model=FAST_MODEL,
        api_key=_get_api_key(),
        temperature=0.1,  # low temp for structured output
        max_tokens=2048,
        request_timeout=30,
    )


@lru_cache(maxsize=2)
def get_quality_llm() -> ChatGroq:
    """
    Returns llama-3.3-70b-versatile — use for:
    - FIRE/Tax/Portfolio narration
    - Behavioral intervention messages
    - Literacy micro-lessons and quiz generation
    - Audit trail narration
    """
    return ChatGroq(
        model=QUALITY_MODEL,
        api_key=_get_api_key(),
        temperature=0.4,  # moderate creativity for narration
        max_tokens=4096,
        request_timeout=60,
    )


# ─── Safe Invoke Wrappers ────────────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((Exception,)),
    reraise=True,
)
async def invoke_fast(prompt: str) -> str:
    """
    Call the fast LLM (8B) with rate limiting and retry.
    Returns the raw text content.
    """
    _rate_limiter.wait_if_needed()
    llm = get_fast_llm()
    try:
        response = await llm.ainvoke(prompt)
        return response.content
    except Exception as e:
        logger.error(f"Fast LLM invoke failed: {e}")
        raise


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((Exception,)),
    reraise=True,
)
async def invoke_quality(prompt: str) -> str:
    """
    Call the quality LLM (70B) with rate limiting and retry.
    Returns the raw text content.
    """
    _rate_limiter.wait_if_needed()
    llm = get_quality_llm()
    try:
        response = await llm.ainvoke(prompt)
        return response.content
    except Exception as e:
        logger.error(f"Quality LLM invoke failed: {e}")
        raise


async def safe_invoke_fast(prompt: str, fallback: str = "") -> str:
    """Call fast LLM, return fallback string on any error."""
    try:
        return await invoke_fast(prompt)
    except Exception as e:
        logger.error(f"Fast LLM failed after retries: {e}")
        return fallback


async def safe_invoke_quality(prompt: str, fallback: str = "") -> str:
    """Call quality LLM, return fallback string on any error."""
    try:
        return await invoke_quality(prompt)
    except Exception as e:
        logger.error(f"Quality LLM failed after retries: {e}")
        return fallback
