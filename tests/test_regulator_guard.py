"""
Tests for Regulator Guard Agent — verifies compliance checking logic.
"""

import pytest

from agents.regulator_guard import (
    _check_blocked_phrases,
    _check_return_assumptions,
    _check_section_limits,
    _apply_fixes,
)


class TestBlockedPhrases:
    """Test hard-block phrase detection."""

    def test_catches_guaranteed_return(self):
        text = "This investment gives guaranteed return of 15%"
        flags = _check_blocked_phrases(text)
        assert len(flags) > 0
        assert flags[0]["type"] == "BLOCK"

    def test_catches_sure_shot(self):
        text = "Yeh sure shot profit dega"
        flags = _check_blocked_phrases(text)
        assert len(flags) > 0

    def test_catches_risk_free(self):
        text = "This is a risk free investment"
        flags = _check_blocked_phrases(text)
        assert len(flags) > 0

    def test_clean_text_no_flags(self):
        text = "Market mein invest karo, returns market conditions pe depend karte hain"
        flags = _check_blocked_phrases(text)
        assert len(flags) == 0

    def test_catches_double_your_money(self):
        text = "Double your money in 3 years"
        flags = _check_blocked_phrases(text)
        assert len(flags) > 0


class TestReturnAssumptions:
    """Test unrealistic return detection."""

    def test_catches_high_equity_return(self):
        text = "Assuming 15% return on equity investments"
        flags = _check_return_assumptions(text)
        assert len(flags) > 0
        assert "RETURN_ASSUMPTION" in flags[0]["rule"]

    def test_accepts_reasonable_return(self):
        text = "Assuming 12% return on equity"
        flags = _check_return_assumptions(text)
        assert len(flags) == 0

    def test_catches_20_percent(self):
        text = "You can expect 20% CAGR growth"
        flags = _check_return_assumptions(text)
        assert len(flags) > 0


class TestSectionLimits:
    """Test wrong tax section limit detection."""

    def test_catches_wrong_80c_limit(self):
        text = "Section 80C allows deduction up to ₹2,00,000"
        flags = _check_section_limits(text)
        assert len(flags) > 0
        assert flags[0]["type"] == "BLOCK"

    def test_accepts_correct_80c_limit(self):
        text = "Section 80C limit is ₹1,50,000"
        flags = _check_section_limits(text)
        assert len(flags) == 0


class TestApplyFixes:
    """Test fix application."""

    def test_removes_blocked_phrase(self):
        text = "This is a guaranteed return investment"
        flags = [{"type": "BLOCK", "rule": "SEBI_PROHIBITED_CLAIMS", "original_text": "guaranteed return"}]
        fixed = _apply_fixes(text, flags)
        assert "guaranteed return" not in fixed

    def test_replaces_high_return(self):
        text = "Assuming 15% return"
        flags = [{"type": "FLAG", "rule": "SEBI_RETURN_ASSUMPTION", "original_text": "15%"}]
        fixed = _apply_fixes(text, flags)
        assert "12%" in fixed
