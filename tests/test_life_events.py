"""
Tests for Life Events Detection.
"""

import pytest

from integrations.life_events import _regex_detect, _extract_amount


class TestRegexDetection:
    """Test regex-based event detection."""

    def test_detects_bonus(self):
        event, conf = _regex_detect("Mujhe 5 lakh ka bonus mila hai")
        assert event == "income_increase"
        assert conf >= 0.7

    def test_detects_marriage(self):
        event, conf = _regex_detect("Meri shaadi hone wali hai next year")
        assert event == "marriage"

    def test_detects_job_loss(self):
        event, conf = _regex_detect("Main apni job se resign kar raha hoon")
        assert event == "income_loss"

    def test_detects_baby(self):
        event, conf = _regex_detect("Wife pregnant hai, baby aa raha hai")
        assert event == "new_child"

    def test_detects_home_purchase(self):
        event, conf = _regex_detect("Flat kharidna chahta hoon")
        assert event == "home_purchase"

    def test_no_event(self):
        event, conf = _regex_detect("Aaj mausam accha hai")
        assert event == "none"
        assert conf == 0.0


class TestAmountExtraction:
    """Test monetary amount extraction."""

    def test_extracts_lakh(self):
        amount = _extract_amount("5 lakh ka bonus mila")
        assert amount == 500000

    def test_extracts_crore(self):
        amount = _extract_amount("₹1.5 crore ka ghar")
        assert amount == 15000000

    def test_extracts_rupee_symbol(self):
        amount = _extract_amount("₹5 lakh invest kiya")
        assert amount == 500000

    def test_no_amount(self):
        amount = _extract_amount("Job change kar raha hoon")
        assert amount is None
