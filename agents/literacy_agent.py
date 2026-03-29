"""
Agent 8: Financial Literacy Agent 🔥
Generates dynamic "Did you know?" micro-lessons and quizzes
tied to the user's own numbers. Tracks literacy improvement.
Uses llama-3.3-70b-versatile for quality content.
"""

from __future__ import annotations

import json
import logging

from integrations.groq_client import safe_invoke_quality
from prompts.literacy_prompts import (
    MICRO_LESSON_PROMPT,
    QUIZ_GENERATION_PROMPT,
)

logger = logging.getLogger("astraguard.agents.literacy")


# ─── Difficulty Mapping ──────────────────────────────────────────────────────

def _get_difficulty(score: int) -> str:
    """Map literacy score to quiz difficulty."""
    if score < 30:
        return "EASY"
    elif score <= 60:
        return "MEDIUM"
    else:
        return "HARD"


# ─── Dimension Mapping ──────────────────────────────────────────────────────

CALC_TO_DIMENSION = {
    "fire": "fire",
    "tax": "tax",
    "portfolio": "mutual_funds",
    "insurance": "insurance",
}


def _parse_json_response(raw: str) -> dict:
    """Parse LLM response to JSON."""
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(raw[start:end])
            except json.JSONDecodeError:
                pass
    return {}


def compute_score_update(correct_count: int, total: int = 3) -> int:
    """Compute literacy score delta based on quiz results."""
    if correct_count == total:
        return 15
    elif correct_count >= total * 0.66:
        return 10
    elif correct_count >= total * 0.33:
        return 5
    else:
        return 2  # engagement credit


async def generate_micro_lesson(
    calculation_type: str,
    calculation_result: dict,
    financial_dna: dict,
    literacy_scores: dict | None = None,
) -> dict:
    """
    Generate a "Did you know?" micro-lesson tied to the user's own data.

    Returns:
        {
            "lesson_title": str,
            "lesson_body": str,
            "concept_taught": str,
            "literacy_dimension": str,
        }
    """
    dimension = CALC_TO_DIMENSION.get(calculation_type, "fire")
    scores = literacy_scores or {}

    prompt = MICRO_LESSON_PROMPT.format(
        calculation_type=calculation_type,
        calculation_result=json.dumps(calculation_result, indent=2, default=str)[:2000],
        age=financial_dna.get("age", "N/A"),
        salary=financial_dna.get("annual_salary", "N/A"),
        investments=json.dumps(financial_dna.get("existing_investments", {}), default=str),
        literacy_scores=json.dumps(scores, default=str),
    )

    raw_response = await safe_invoke_quality(prompt, fallback="")
    lesson = _parse_json_response(raw_response)

    if not lesson:
        lesson = {
            "lesson_title": "💡 Financial Insight",
            "lesson_body": "Detailed insights are being generated. Check back shortly!",
            "concept_taught": calculation_type,
            "literacy_dimension": dimension,
        }

    return lesson


async def generate_quiz(
    calculation_type: str,
    calculation_result: dict,
    literacy_scores: dict | None = None,
) -> dict:
    """
    Generate a 3-question adaptive quiz based on the calculation.

    Returns:
        {
            "quiz_topic": str,
            "difficulty": str,
            "questions": [
                {
                    "question": str,
                    "options": [str, str, str, str],
                    "correct_index": int,
                    "explanation": str,
                    "concept": str,
                }
            ]
        }
    """
    dimension = CALC_TO_DIMENSION.get(calculation_type, "fire")
    scores = literacy_scores or {}
    current_score = scores.get(dimension, 0)
    difficulty = _get_difficulty(current_score)

    prompt = QUIZ_GENERATION_PROMPT.format(
        topic=dimension,
        calculation_type=calculation_type,
        calculation_context=json.dumps(calculation_result, indent=2, default=str)[:2000],
        current_score=current_score,
        difficulty=difficulty,
    )

    raw_response = await safe_invoke_quality(prompt, fallback="")
    quiz = _parse_json_response(raw_response)

    if not quiz or "questions" not in quiz:
        quiz = {
            "quiz_topic": dimension,
            "difficulty": difficulty,
            "questions": [],
        }

    return quiz


async def run_literacy_agent(
    user_id: str,
    calculation_type: str,
    calculation_result: dict,
    financial_dna: dict,
    current_literacy_scores: dict | None = None,
) -> dict:
    """
    Full literacy agent run — generates micro-lesson + quiz.

    Args:
        user_id: User identifier
        calculation_type: "fire", "tax", "portfolio"
        calculation_result: Raw math engine output
        financial_dna: User's financial profile
        current_literacy_scores: Current scores per dimension

    Returns:
        {
            "micro_lesson": dict,
            "quiz": dict,
            "literacy_dimension": str,
            "estimated_score_after": int,
        }
    """
    dimension = CALC_TO_DIMENSION.get(calculation_type, "fire")
    scores = current_literacy_scores or {}
    current_score = scores.get(dimension, 0)

    # Generate both in parallel-ish (both async)
    lesson = await generate_micro_lesson(
        calculation_type, calculation_result, financial_dna, scores
    )
    quiz = await generate_quiz(
        calculation_type, calculation_result, scores
    )

    # Estimated score after engaging with lesson + perfect quiz
    estimated_after = min(current_score + 15 + 3, 100)  # +15 for quiz + 3 for lesson read

    return {
        "micro_lesson": lesson,
        "quiz": quiz,
        "literacy_dimension": dimension,
        "estimated_score_after": estimated_after,
    }
