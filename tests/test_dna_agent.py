"""
Tests for DNA Agent — verifies extraction logic and question flow.
"""

import pytest
import json

# Import the functions we want to test
from agents.dna_agent import (
    _calculate_completion,
    _is_extraction_complete,
    _get_next_question,
    _parse_llm_response,
)


class TestCompletion:
    """Test completion percentage calculation."""

    def test_empty_profile_zero_completion(self):
        extracted = {"financial_dna": {}, "behavioral_dna": {}}
        assert _calculate_completion(extracted) == 0

    def test_partial_profile(self):
        extracted = {
            "financial_dna": {
                "age": 28,
                "annual_salary": 1800000,
                "monthly_expenses": None,
            },
            "behavioral_dna": {},
        }
        completion = _calculate_completion(extracted)
        assert 10 <= completion <= 30  # 2 of ~11 fields

    def test_full_profile_high_completion(self):
        extracted = {
            "financial_dna": {
                "age": 28,
                "annual_salary": 1800000,
                "monthly_expenses": 60000,
                "goals": [{"name": "Retirement", "target_amount": 50000000}],
                "insurance_cover": 5000000,
                "risk_profile": "moderate",
                "city_type": "metro",
                "existing_investments": {"mutual_funds": 500000, "ppf": 100000},
            },
            "behavioral_dna": {
                "panic_threshold": -17.0,
                "behavior_type": "panic_prone",
                "last_panic_event": "COVID 2020",
            },
        }
        completion = _calculate_completion(extracted)
        assert completion >= 80


class TestExtractionComplete:
    """Test minimum field requirement check."""

    def test_incomplete_no_age(self):
        extracted = {"financial_dna": {"annual_salary": 1800000, "monthly_expenses": 60000, "goals": [{"name": "Retire"}]}}
        assert _is_extraction_complete(extracted) is False

    def test_incomplete_no_goals(self):
        extracted = {"financial_dna": {"age": 28, "annual_salary": 1800000, "monthly_expenses": 60000, "goals": []}}
        assert _is_extraction_complete(extracted) is False

    def test_complete_minimum(self):
        extracted = {"financial_dna": {"age": 28, "annual_salary": 1800000, "monthly_expenses": 60000, "goals": [{"name": "Retire"}]}}
        assert _is_extraction_complete(extracted) is True


class TestNextQuestion:
    """Test question flow logic."""

    def test_first_question_is_age(self):
        extracted = {"financial_dna": {}, "behavioral_dna": {}}
        q = _get_next_question(extracted, 0)
        assert "umar" in q.lower() or "age" in q.lower()

    def test_asks_salary_after_age(self):
        extracted = {"financial_dna": {"age": 28}, "behavioral_dna": {}}
        q = _get_next_question(extracted, 1)
        assert "salary" in q.lower()


class TestParseResponse:
    """Test JSON parsing resilience."""

    def test_clean_json(self):
        raw = '{"status": "gathering", "financial_dna": {"age": 28}}'
        result = _parse_llm_response(raw)
        assert result["financial_dna"]["age"] == 28

    def test_json_in_markdown(self):
        raw = '```json\n{"status": "complete", "financial_dna": {"age": 34}}\n```'
        result = _parse_llm_response(raw)
        assert result["financial_dna"]["age"] == 34

    def test_json_with_extra_text(self):
        raw = 'Here is the result: {"status": "gathering"} hope this helps'
        result = _parse_llm_response(raw)
        assert result["status"] == "gathering"

    def test_invalid_json(self):
        raw = "This is not JSON at all"
        result = _parse_llm_response(raw)
        assert result == {}
