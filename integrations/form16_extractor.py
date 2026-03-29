"""
Form 16 PDF Extractor — extracts financial data from uploaded Form 16.

Approach:
1. Extract raw text from PDF (pdfplumber for text + tables, PyPDF2 fallback)
2. Use regex to pull structured fields (salary, HRA, 80C, 80D, etc.)
3. Use LLM (llama3-8b) as fallback for complex/messy PDFs
4. Map extracted data directly into FinancialDNA schema

Form 16 Structure (as per Income-tax Fifth Amendment Rules, 2023):
  Part A: TDS Certificate (employer details, TAN, PAN, TDS summary)
  Part B (Annexure-I): Salary breakup, deductions, tax computation (employees)
  Part B (Annexure-II): For specified senior citizens (pension + interest)
"""

from __future__ import annotations

import re
import json
import logging
from pathlib import Path

logger = logging.getLogger("astraguard.integrations.form16")

MAX_FILE_SIZE_MB = 10

# Minimum amount threshold — anything below this is likely a section number
# (e.g., "17(1)" → 17, "80C" → 80) and NOT an actual Rs. amount
MIN_VALID_AMOUNT = 100  # ₹100 is the floor for any real financial value


# ═══════════════════════════════════════════════════════════════════════
# AMOUNT EXTRACTION HELPER
# ═══════════════════════════════════════════════════════════════════════

def _parse_amount(value: str) -> float:
    """Parse Indian-format number string to float."""
    if not value:
        return 0.0
    cleaned = value.replace(",", "").replace("₹", "").replace("Rs.", "").replace("Rs", "").strip()
    # Skip blank template placeholders
    if cleaned in ("...", "…", "....", "…."):
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _extract_rs_amount(text: str, label_pattern: str) -> float:
    """
    Extract Rs. amount that follows a label in Form 16 format.
    
    Handles these patterns:
        "Gross Salary Rs. 18,00,000"
        "section 80C    Rs. 1,50,000   Rs. 1,50,000"
        "Total Tax Payable  ₹2,10,600"
        "Standard deduction under section 16(ia) Rs. 75,000"
    
    Returns 0.0 if value is blank ("Rs. ...") or not found.
    """
    # Pattern: label ... Rs. <amount> (or ₹<amount>)
    # The amount must be 3+ digits (to skip section numbers like 17, 80)
    pattern = label_pattern + r'.*?(?:Rs\.?\s*|₹\s*)([\d,]+(?:\.\d{2})?)'
    matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
    
    if matches:
        # Take the LAST match since Form 16 often has "Gross Amount" then "Deductible Amount"
        # The last column (deductible) is what we want
        for match in reversed(matches):
            amount = _parse_amount(match)
            if amount >= MIN_VALID_AMOUNT:
                return amount
    return 0.0


# ═══════════════════════════════════════════════════════════════════════
# FORM 16 PART B (Annexure-I) — Line-by-line extraction
# Based on actual Form 16 structure from IT Rules
# ═══════════════════════════════════════════════════════════════════════

def _extract_with_regex(text: str) -> dict:
    """
    Extract all fields from Form 16 text using the actual Form 16 structure.
    Designed to handle both text-based PDFs and tabular layouts.
    """
    extracted = {}
    
    # === SALARY SECTION (Lines 1-3) ===
    
    # 1(a) Salary as per section 17(1)
    val = _extract_rs_amount(text, r'Salary\s*as\s*per\s*(?:provisions\s*)?(?:contained\s*in\s*)?(?:section\s*)?17\(1\)')
    if val: extracted["salary_us_17_1"] = val
    
    # 1(b) Value of perquisites 17(2)
    val = _extract_rs_amount(text, r'(?:Value\s*of\s*)?[Pp]erquisites.*?17\(2\)')
    if val: extracted["perquisites_17_2"] = val
    
    # 1(c) Profits in lieu of salary 17(3)
    val = _extract_rs_amount(text, r'[Pp]rofits\s*in\s*lieu.*?17\(3\)')
    if val: extracted["profits_lieu_17_3"] = val
    
    # 1(d) Total Gross Salary — most commonly "Gross Salary" or "Total" after 1(c)
    val = _extract_rs_amount(text, r'(?:Gross\s*Salary|1\s*\.\s*Gross\s*Salary|1\(d\)\s*Total)')
    if not val:
        # Try: "Total Rs. X" in salary section
        val = _extract_rs_amount(text, r'\(d\)\s*Total')
    if val: extracted["gross_salary"] = val
    
    # === EXEMPTIONS SECTION (Line 2) ===
    
    # 2(e) House Rent Allowance u/s 10(13A)
    val = _extract_rs_amount(text, r'[Hh]ouse\s*[Rr]ent\s*[Aa]llowance.*?10\(13A\)')
    if not val:
        val = _extract_rs_amount(text, r'10\(13A\)')
    if val: extracted["hra_received"] = val
    
    # 2(i) Total exemptions under section 10
    val = _extract_rs_amount(text, r'[Tt]otal\s*(?:amount\s*of\s*)?exemption.*?(?:section\s*)?10')
    if val: extracted["total_exemptions_s10"] = val
    
    # === DEDUCTIONS SECTION 16 (Lines 4-5) ===
    
    # 4(a) / 3(a) Standard deduction u/s 16(ia)
    val = _extract_rs_amount(text, r'[Ss]tandard\s*[Dd]eduction.*?16\(ia\)')
    if not val:
        val = _extract_rs_amount(text, r'[Ss]tandard\s*[Dd]eduction')
    if val: extracted["standard_deduction"] = val
    
    # 4(b) Entertainment allowance u/s 16(ii)
    val = _extract_rs_amount(text, r'[Ee]ntertainment\s*[Aa]llowance.*?16\(ii\)')
    if val: extracted["entertainment_allowance"] = val
    
    # 4(c) / 3(b) Professional tax / Tax on employment u/s 16(iii)
    val = _extract_rs_amount(text, r'[Tt]ax\s*on\s*employment.*?16\(iii\)')
    if not val:
        val = _extract_rs_amount(text, r'[Pp]rofessional\s*[Tt]ax')
    if val: extracted["professional_tax"] = val
    
    # === INCOME FROM HOUSE PROPERTY (Line 7a) ===
    
    # 7(a) Income from house property (often negative = home loan interest)
    # Use specialized extraction since it's often negative: "Rs. -1,85,000"
    hp_match = re.search(
        r'[Ii]ncome\s*(?:from\s*)?[Hh]ouse\s*[Pp]roperty.*?Rs\.?\s*-?\s*([\d,]+(?:\.\d{2})?)',
        text
    )
    if hp_match:
        hp_val = _parse_amount(hp_match.group(1))
        if hp_val >= MIN_VALID_AMOUNT:
            extracted["home_loan_interest_24b"] = hp_val
    
    # === GROSS TOTAL INCOME (Line 9) ===
    
    val = _extract_rs_amount(text, r'[Gg]ross\s*[Tt]otal\s*[Ii]ncome')
    if val: extracted["gross_total_income"] = val
    
    # === CHAPTER VI-A DEDUCTIONS (Line 10) ===
    
    # 10(a) / 8(a) Section 80C — life insurance, PF, etc.
    val = _extract_rs_amount(text, r'(?:life\s*insurance|provident\s*fund).*?(?:section\s*)?80C\b')
    if not val:
        val = _extract_rs_amount(text, r'\(a\).*?section\s*80C\b')
    if val: extracted["deduction_80c"] = val
    
    # 10(b) / 8(b) Section 80CCC — pension funds
    val = _extract_rs_amount(text, r'(?:pension\s*funds|certain\s*pension).*?(?:section\s*)?80CCC\b')
    if val: extracted["deduction_80ccc"] = val
    
    # 10(c) / 8(c) Section 80CCD(1) — employee NPS
    val = _extract_rs_amount(text, r'(?:taxpayer\s*to\s*pension|contribution\s*by\s*taxpayer).*?80CCD\s*\(1\)')
    if not val:
        val = _extract_rs_amount(text, r'80CCD\s*\(1\)[^B]')
    if val: extracted["deduction_80ccd_1"] = val
    
    # 10(d) / 8(d) Total of 80C + 80CCC + 80CCD(1) — capped at ₹1.5L
    val = _extract_rs_amount(text, r'[Tt]otal\s*deduction.*?80C.*?80CCC.*?80CCD')
    if val: extracted["total_80c_80ccc_80ccd1"] = val
    
    # 10(e) / 8(e) Section 80CCD(1B) — additional NPS ₹50K
    val = _extract_rs_amount(text, r'(?:notified\s*pension|80CCD\s*\(1B\))')
    if val: extracted["deduction_80ccd_1b"] = val
    
    # 10(f) / 8(f) Section 80CCD(2) — employer NPS contribution
    val = _extract_rs_amount(text, r'(?:contribution\s*by\s*[Ee]mployer.*?pension|80CCD\s*\(2\))')
    if val: extracted["deduction_80ccd_2"] = val
    
    # 10(g) / 8(f for senior) Section 80D — health insurance
    val = _extract_rs_amount(text, r'[Hh]ealth\s*[Ii]nsurance.*?(?:section\s*)?80D\b')
    if not val:
        val = _extract_rs_amount(text, r'(?:section\s*)?80D\b')
    if val: extracted["deduction_80d"] = val
    
    # 10(h) / 8(g) Section 80E — education loan interest
    val = _extract_rs_amount(text, r'(?:higher\s*education|loan.*?education).*?(?:section\s*)?80E\b')
    if val: extracted["deduction_80e"] = val
    
    # 10(i) Section 80CCH — Agnipath Scheme (new)
    val = _extract_rs_amount(text, r'[Aa]gnipath.*?80CCH')
    if val: extracted["deduction_80cch"] = val
    
    # 10(k) / 8(h) Section 80G — donations
    val = _extract_rs_amount(text, r'[Dd]onations.*?(?:section\s*)?80G\b')
    if val: extracted["deduction_80g"] = val
    
    # 10(l) / 8(i) Section 80TTA — savings interest
    val = _extract_rs_amount(text, r'(?:savings\s*account|deposits\s*in\s*savings).*?80TTA\b')
    if val: extracted["deduction_80tta"] = val
    
    # Section 80TTB — senior citizen savings interest
    val = _extract_rs_amount(text, r'(?:savings\s*account|deposits\s*in\s*savings).*?80TTB\b')
    if val: extracted["deduction_80ttb"] = val
    
    # 11 / 9: Aggregate deductions Chapter VI-A
    val = _extract_rs_amount(text, r'[Aa]ggregate.*?[Dd]eductible.*?Chapter\s*VI')
    if val: extracted["total_chapter_via_deductions"] = val
    
    # === TAX COMPUTATION (Lines 12-19) ===
    
    # 12 / 10: Total taxable income
    val = _extract_rs_amount(text, r'[Tt]otal\s*[Tt]axable\s*[Ii]ncome')
    if val: extracted["total_taxable_income"] = val
    
    # 13 / 11: Tax on total income
    val = _extract_rs_amount(text, r'[Tt]ax\s*on\s*[Tt]otal\s*[Ii]ncome')
    if val: extracted["tax_on_total_income"] = val
    
    # Also try: Total income (gross)
    val = _extract_rs_amount(text, r'[Tt]otal\s*[Ii]ncome(?:\s*\()')
    if val: extracted.setdefault("total_income", val)
    
    # 14 / 12: Rebate u/s 87A
    val = _extract_rs_amount(text, r'[Rr]ebate.*?(?:section\s*)?87A')
    if val: extracted["rebate_87a"] = val
    
    # 15 / 13: Surcharge
    val = _extract_rs_amount(text, r'[Ss]urcharge')
    if val: extracted["surcharge"] = val
    
    # 16 / 14: Health and education cess
    val = _extract_rs_amount(text, r'[Hh]ealth\s*(?:and|&)\s*[Ee]ducation\s*[Cc]ess')
    if not val:
        val = _extract_rs_amount(text, r'[Cc]ess\s*@?\s*4%?')
    if val: extracted["health_education_cess"] = val
    
    # 17 / 15: Tax payable
    val = _extract_rs_amount(text, r'[Tt]ax\s*[Pp]ayable')
    if val: extracted["tax_payable"] = val
    
    # 18 / 16: Relief u/s 89
    val = _extract_rs_amount(text, r'[Rr]elief.*?(?:section\s*)?89')
    if val: extracted["relief_89"] = val
    
    # 19 / 17: Net tax payable
    val = _extract_rs_amount(text, r'[Nn]et\s*[Tt]ax\s*[Pp]ayable')
    if val: extracted["net_tax_payable"] = val
    
    # === TAX DEDUCTED (Part A) ===
    
    # Total TDS
    total_tds_pattern = r'[Tt]otal\s*(?:\(\s*Rs\.?\s*\)|.*?TDS)'
    val = _extract_rs_amount(text, total_tds_pattern)
    if val: extracted["tax_deducted"] = val
    
    # === METADATA ===
    
    # PAN
    pan_match = re.search(r'PAN\s*(?:of\s*(?:the\s*)?Employee)?[^A-Z]*([A-Z]{5}\d{4}[A-Z])', text)
    if pan_match:
        extracted["pan"] = pan_match.group(1)
    
    # Assessment Year
    ay_match = re.search(r'[Aa]ssessment\s*[Yy]ear\s*[:\-]?\s*(\d{4}\s*-\s*\d{2,4})', text)
    if ay_match:
        extracted["assessment_year"] = ay_match.group(1).strip()
    
    # Financial Year
    fy_match = re.search(r'[Ff]inancial\s*[Yy]ear\s*[:\-]?\s*(\d{4}\s*-\s*\d{2,4})', text)
    if fy_match:
        extracted["financial_year"] = fy_match.group(1).strip()
    
    # Employer name
    emp_match = re.search(r'[Nn]ame\s*(?:and\s*[Aa]ddress\s*)?of\s*(?:the\s*)?[Ee]mployer\s*[/:]?\s*(.+?)(?:\n|Employee|$)', text)
    if emp_match:
        name = emp_match.group(1).strip()
        # Clean up template text
        if name and "……" not in name and "..." not in name and len(name) > 3:
            extracted["employer_name"] = name
    
    # Employee name  
    emp_name_match = re.search(r'[Nn]ame\s*(?:and\s*[Aa]ddress\s*)?of\s*(?:the\s*)?[Ee]mployee\s*[/:]?\s*(.+?)(?:\n|$)', text)
    if emp_name_match:
        name = emp_name_match.group(1).strip()
        if name and "……" not in name and "..." not in name and len(name) > 3:
            extracted["employee_name"] = name

    # TAN of deductor
    tan_match = re.search(r'TAN\s*(?:of\s*(?:the\s*)?[Dd]eductor)?[^A-Z]*([A-Z]{4}\d{5}[A-Z])', text)
    if tan_match:
        extracted["tan"] = tan_match.group(1)
    
    # Opt-out of 115BAC
    if re.search(r'115BAC.*?YES', text, re.IGNORECASE):
        extracted["opted_out_115bac"] = True
    elif re.search(r'115BAC.*?NO', text, re.IGNORECASE):
        extracted["opted_out_115bac"] = False
    
    # === EPF (not standard Form 16 field but sometimes embedded) ===
    val = _extract_rs_amount(text, r'[Ee]mployee.*?[Pp]rovident\s*[Ff]und|EPF')
    if val: extracted["epf_contribution"] = val
    
    # === Derive total_income if not found ===
    if "total_income" not in extracted:
        if "total_taxable_income" in extracted:
            extracted["total_income"] = extracted["total_taxable_income"]
        elif "gross_total_income" in extracted:
            extracted["total_income"] = extracted["gross_total_income"]
    
    # === Derive total_tax if not found ===
    if "total_tax" not in extracted:
        if "net_tax_payable" in extracted:
            extracted["total_tax"] = extracted["net_tax_payable"]
        elif "tax_payable" in extracted:
            extracted["total_tax"] = extracted["tax_payable"]
        elif "tax_on_total_income" in extracted:
            extracted["total_tax"] = extracted["tax_on_total_income"]
    
    return extracted


def _extract_from_tables(pdf_path: str) -> dict:
    """
    Extract fields from PDF tables using pdfplumber's table extraction.
    Many Form 16 PDFs use structured tables.
    """
    extracted = {}
    try:
        import pdfplumber

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if not row or len(row) < 2:
                            continue
                        # Clean None values
                        cells = [str(c).strip() if c else "" for c in row]
                        label = " ".join(cells[:-1]).strip().lower()
                        
                        # Find the last cell with an Rs. amount
                        amount = 0.0
                        for cell in reversed(cells):
                            cell_clean = cell.replace("Rs.", "").replace("₹", "").replace(",", "").strip()
                            if cell_clean and cell_clean not in ("...", "…", ""):
                                try:
                                    val = float(cell_clean)
                                    if val >= MIN_VALID_AMOUNT:
                                        amount = val
                                        break
                                except ValueError:
                                    continue

                        if not label or amount == 0:
                            continue

                        # Map table labels to fields
                        if "17(1)" in label or ("salary" in label and "gross" not in label):
                            extracted.setdefault("salary_us_17_1", amount)
                        elif "gross salary" in label or "(d) total" in label:
                            extracted.setdefault("gross_salary", amount)
                        elif "10(13a)" in label or "house rent allowance" in label:
                            extracted.setdefault("hra_received", amount)
                        elif "standard deduction" in label or "16(ia)" in label:
                            extracted.setdefault("standard_deduction", amount)
                        elif "tax on employment" in label or "16(iii)" in label or "professional tax" in label:
                            extracted.setdefault("professional_tax", amount)
                        elif "80ccd(1b)" in label or "80ccd (1b)" in label:
                            extracted.setdefault("deduction_80ccd_1b", amount)
                        elif "80ccd(2)" in label or "80ccd (2)" in label:
                            extracted.setdefault("deduction_80ccd_2", amount)
                        elif "80ccd(1)" in label or "80ccd (1)" in label:
                            extracted.setdefault("deduction_80ccd_1", amount)
                        elif re.search(r'\b80c\b', label) and "80cc" not in label:
                            extracted.setdefault("deduction_80c", amount)
                        elif re.search(r'\b80d\b', label):
                            extracted.setdefault("deduction_80d", amount)
                        elif re.search(r'\b80e\b', label):
                            extracted.setdefault("deduction_80e", amount)
                        elif re.search(r'\b80g\b', label):
                            extracted.setdefault("deduction_80g", amount)
                        elif re.search(r'\b80tta\b', label):
                            extracted.setdefault("deduction_80tta", amount)
                        elif re.search(r'\b80ttb\b', label):
                            extracted.setdefault("deduction_80ttb", amount)
                        elif "80ccc" in label:
                            extracted.setdefault("deduction_80ccc", amount)
                        elif "house property" in label or "24(b)" in label:
                            extracted.setdefault("home_loan_interest_24b", abs(amount))
                        elif "gross total income" in label:
                            extracted.setdefault("gross_total_income", amount)
                        elif "total taxable income" in label:
                            extracted.setdefault("total_taxable_income", amount)
                        elif "tax on total income" in label:
                            extracted.setdefault("tax_on_total_income", amount)
                        elif "net tax payable" in label:
                            extracted.setdefault("net_tax_payable", amount)
                        elif "tax payable" in label:
                            extracted.setdefault("tax_payable", amount)
                        elif "surcharge" in label:
                            extracted.setdefault("surcharge", amount)
                        elif "cess" in label:
                            extracted.setdefault("health_education_cess", amount)
                        elif "relief" in label and "89" in label:
                            extracted.setdefault("relief_89", amount)
                        elif "rebate" in label and "87a" in label:
                            extracted.setdefault("rebate_87a", amount)
                        elif "aggregate" in label and "chapter vi" in label:
                            extracted.setdefault("total_chapter_via_deductions", amount)

    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Table extraction failed: {e}")

    return extracted


# ═══════════════════════════════════════════════════════════════════════
# MAP TO FINANCIAL DNA
# ═══════════════════════════════════════════════════════════════════════

def _map_to_financial_dna(extracted: dict) -> dict:
    """Map extracted Form 16 fields to FinancialDNA schema."""
    annual_salary = extracted.get("gross_salary", 0) or extracted.get("salary_us_17_1", 0)

    # Estimate monthly expenses from salary (heuristic: 50% of monthly take-home)
    total_tax = extracted.get("total_tax", 0) or extracted.get("net_tax_payable", 0) or extracted.get("tax_payable", 0)
    monthly_take_home = (annual_salary - total_tax) / 12 if annual_salary else 0
    estimated_monthly_expenses = monthly_take_home * 0.5  # conservative estimate

    # Build existing investments from deductions
    existing_investments = {
        "mutual_funds": 0,
        "ppf": 0,
        "fd": 0,
        "stocks": 0,
        "epf": extracted.get("epf_contribution", 0),
        "nps": extracted.get("deduction_80ccd_1b", 0) + extracted.get("deduction_80ccd_2", 0),
        "gold": 0,
        "real_estate": 0,
    }

    # 80C could be ELSS/PPF/FD/LIC — we can't tell from Form 16 alone
    deduction_80c = extracted.get("deduction_80c", 0)
    if deduction_80c > 0:
        # Attribute to PPF as a safe guess (will be corrected in onboarding)
        existing_investments["ppf"] = deduction_80c

    # Has home loan?
    home_loan_interest = extracted.get("home_loan_interest_24b", 0)
    has_home_loan = home_loan_interest > 0

    # Insurance — 80D gives us health insurance info
    deduction_80d = extracted.get("deduction_80d", 0)

    financial_dna = {
        "annual_salary": annual_salary,
        "monthly_expenses": round(estimated_monthly_expenses, 0) if estimated_monthly_expenses else None,
        "existing_investments": existing_investments,
        "insurance_cover": None,  # not directly in Form 16
        "risk_profile": None,    # not in Form 16
        "has_home_loan": has_home_loan,
        "home_loan_interest_annual": home_loan_interest if has_home_loan else None,
        "hra_received": extracted.get("hra_received"),
        "rent_paid_monthly": None,  # not in Form 16
        "has_health_insurance": deduction_80d > 0,
        "health_insurance_premium": deduction_80d if deduction_80d > 0 else None,
    }

    # Tax-relevant extracted data (pass to tax engine)
    tax_inputs = {
        "annual_salary": annual_salary,
        "hra_received": extracted.get("hra_received", 0),
        "standard_deduction": extracted.get("standard_deduction", 0),
        "deduction_80c": deduction_80c,
        "deduction_80ccc": extracted.get("deduction_80ccc", 0),
        "deduction_80ccd_1": extracted.get("deduction_80ccd_1", 0),
        "deduction_80ccd_1b": extracted.get("deduction_80ccd_1b", 0),
        "deduction_80ccd_2": extracted.get("deduction_80ccd_2", 0),
        "total_80c_80ccc_80ccd1": extracted.get("total_80c_80ccc_80ccd1", 0),
        "deduction_80d": deduction_80d,
        "deduction_80e": extracted.get("deduction_80e", 0),
        "deduction_80g": extracted.get("deduction_80g", 0),
        "deduction_80tta": extracted.get("deduction_80tta", 0),
        "deduction_80ttb": extracted.get("deduction_80ttb", 0),
        "deduction_80cch": extracted.get("deduction_80cch", 0),
        "total_chapter_via_deductions": extracted.get("total_chapter_via_deductions", 0),
        "home_loan_interest_24b": home_loan_interest,
        "professional_tax": extracted.get("professional_tax", 0),
        "entertainment_allowance": extracted.get("entertainment_allowance", 0),
        "total_exemptions_s10": extracted.get("total_exemptions_s10", 0),
        "gross_total_income": extracted.get("gross_total_income", 0),
        "total_taxable_income": extracted.get("total_taxable_income", 0) or extracted.get("total_income", 0),
        "tax_on_total_income": extracted.get("tax_on_total_income", 0),
        "rebate_87a": extracted.get("rebate_87a", 0),
        "surcharge": extracted.get("surcharge", 0),
        "cess": extracted.get("health_education_cess", 0),
        "tax_payable": extracted.get("tax_payable", 0),
        "relief_89": extracted.get("relief_89", 0),
        "net_tax_payable": extracted.get("net_tax_payable", 0) or extracted.get("total_tax", 0),
        "tax_deducted": extracted.get("tax_deducted", 0),
        "epf_contribution": extracted.get("epf_contribution", 0),
        "opted_out_115bac": extracted.get("opted_out_115bac"),
    }

    # Metadata
    metadata = {
        "pan": extracted.get("pan"),
        "tan": extracted.get("tan"),
        "assessment_year": extracted.get("assessment_year"),
        "financial_year": extracted.get("financial_year"),
        "employer_name": extracted.get("employer_name"),
        "employee_name": extracted.get("employee_name"),
        "source": "form16_upload",
    }

    return {
        "financial_dna": financial_dna,
        "tax_inputs": tax_inputs,
        "metadata": metadata,
    }


# ═══════════════════════════════════════════════════════════════════════
# MAIN EXTRACTION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

async def extract_from_pdf(pdf_path: str | Path) -> dict:
    """
    Extract financial data from a Form 16 PDF.

    Args:
        pdf_path: Path to the Form 16 PDF file

    Returns:
        {
            "success": bool,
            "financial_dna": dict,    # mapped to FinancialDNA schema
            "tax_inputs": dict,       # ready for tax_engine.calculate()
            "raw_extracted": dict,    # raw field values
            "metadata": dict,         # PAN, AY, employer
            "fields_found": int,      # how many fields extracted
            "fields_missing": list,   # which fields couldn't be found
            "extraction_method": str, # "pdfplumber" | "llm_fallback"
            "error": str | None,
        }
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        return {"success": False, "error": f"File not found: {pdf_path}"}

    if not pdf_path.suffix.lower() == ".pdf":
        return {"success": False, "error": "File must be a PDF"}

    # File size check
    file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        return {"success": False, "error": f"File too large ({file_size_mb:.1f}MB). Max: {MAX_FILE_SIZE_MB}MB"}

    # ── Step 1: Extract text from PDF ─────────────────────────────────
    raw_text = ""
    extraction_method = "pdfplumber"

    try:
        import pdfplumber

        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    raw_text += page_text + "\n"

    except ImportError:
        logger.warning("pdfplumber not installed. Trying PyPDF2...")
        try:
            from PyPDF2 import PdfReader

            reader = PdfReader(str(pdf_path))
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    raw_text += page_text + "\n"
            extraction_method = "pypdf2"
        except ImportError:
            return {
                "success": False,
                "error": "Neither pdfplumber nor PyPDF2 installed. Run: pip install pdfplumber",
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to read PDF (may be corrupted or password-protected): {e}",
        }

    if not raw_text.strip():
        return {
            "success": False,
            "error": "Could not extract text from PDF. It may be a scanned image — OCR not yet supported.",
        }

    # Check if this is a blank template
    is_template = raw_text.count("Rs. ...") > 10 or raw_text.count("Rs. …") > 10
    if is_template:
        return {
            "success": False,
            "error": "This appears to be a blank Form 16 template (no actual values). Please upload a filled Form 16 with real data.",
            "is_template": True,
        }

    # ── Step 2: Extract fields with regex from text ───────────────────
    raw_extracted = _extract_with_regex(raw_text)

    # ── Step 2b: Also try table extraction (many Form 16s are tabular) ─
    if extraction_method == "pdfplumber":
        table_extracted = _extract_from_tables(str(pdf_path))
        # Merge: table data fills gaps, doesn't overwrite regex data
        for k, v in table_extracted.items():
            if k not in raw_extracted and v:
                raw_extracted[k] = v

    # ── Step 3: If regex+tables found very few fields, try LLM ───────
    if len(raw_extracted) < 4:
        try:
            llm_result = await _extract_with_llm(raw_text)
            if llm_result and len(llm_result) > len(raw_extracted):
                raw_extracted = {**raw_extracted, **llm_result}
                extraction_method = "llm_fallback"
        except Exception as e:
            logger.warning(f"LLM extraction fallback failed: {e}")

    # ── Step 4: Map to FinancialDNA ───────────────────────────────────
    mapped = _map_to_financial_dna(raw_extracted)

    # ── Step 5: Determine missing fields ──────────────────────────────
    important_fields = [
        "gross_salary", "deduction_80c", "deduction_80d",
        "total_income", "total_tax", "standard_deduction",
    ]
    # Check in both raw_extracted and derived fields
    fields_missing = []
    for f in important_fields:
        val = raw_extracted.get(f, 0)
        if not val or val == 0:
            fields_missing.append(f)

    return {
        "success": True,
        "financial_dna": mapped["financial_dna"],
        "tax_inputs": mapped["tax_inputs"],
        "raw_extracted": raw_extracted,
        "metadata": mapped["metadata"],
        "fields_found": len([v for v in raw_extracted.values() if v and v != 0]),
        "fields_missing": fields_missing,
        "extraction_method": extraction_method,
        "raw_text_preview": raw_text[:500],  # first 500 chars for debugging
        "error": None,
    }


async def _extract_with_llm(text: str) -> dict:
    """
    Fallback: Use llama3-8b to extract fields from messy PDF text.
    Only called if regex finds < 4 fields.
    """
    from integrations.groq_client import safe_invoke_fast

    prompt = f"""Extract financial data from this Form 16 text. This is an Indian salary tax document.

TEXT:
{text[:3000]}

Return ONLY a JSON with these fields (use null if not found, numbers as plain integers WITHOUT commas):
{{
    "gross_salary": <int|null>,
    "hra_received": <int|null>,
    "standard_deduction": <int|null>,
    "deduction_80c": <int|null>,
    "deduction_80ccd_1b": <int|null>,
    "deduction_80d": <int|null>,
    "deduction_80e": <int|null>,
    "deduction_80g": <int|null>,
    "deduction_80tta": <int|null>,
    "home_loan_interest_24b": <int|null>,
    "professional_tax": <int|null>,
    "total_income": <int|null>,
    "total_tax": <int|null>,
    "epf_contribution": <int|null>,
    "surcharge": <int|null>,
    "health_education_cess": <int|null>,
    "pan": "<string|null>",
    "assessment_year": "<string|null>",
    "employer_name": "<string|null>"
}}

IMPORTANT: Only extract actual numeric values. Do NOT extract section numbers (17, 80, 16, etc.) as amounts. Real amounts will be >= 100."""

    raw = await safe_invoke_fast(prompt, fallback="{}")

    # Parse response
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()

    try:
        result = json.loads(raw)
        # Convert nulls and clean up
        cleaned = {}
        for k, v in result.items():
            if v is not None:
                if k in ("pan", "assessment_year", "employer_name"):
                    cleaned[k] = str(v)
                else:
                    val = float(v) if v else 0.0
                    if val >= MIN_VALID_AMOUNT:  # Only keep real amounts
                        cleaned[k] = val
        return cleaned
    except (json.JSONDecodeError, ValueError):
        return {}


async def extract_from_text(raw_text: str) -> dict:
    """
    Extract from raw text directly (for when PDF text is provided by frontend).

    Args:
        raw_text: Raw text content from Form 16

    Returns:
        Same format as extract_from_pdf()
    """
    if not raw_text or not raw_text.strip():
        return {"success": False, "error": "Empty text provided"}

    # Check if blank template
    if raw_text.count("Rs. ...") > 10:
        return {"success": False, "error": "This is a blank Form 16 template.", "is_template": True}

    raw_extracted = _extract_with_regex(raw_text)

    if len(raw_extracted) < 4:
        try:
            llm_result = await _extract_with_llm(raw_text)
            if llm_result and len(llm_result) > len(raw_extracted):
                raw_extracted = {**raw_extracted, **llm_result}
        except Exception:
            pass

    mapped = _map_to_financial_dna(raw_extracted)

    important_fields = [
        "gross_salary", "deduction_80c", "deduction_80d",
        "total_income", "total_tax", "standard_deduction",
    ]
    fields_missing = [f for f in important_fields if f not in raw_extracted or raw_extracted.get(f, 0) == 0]

    return {
        "success": True,
        "financial_dna": mapped["financial_dna"],
        "tax_inputs": mapped["tax_inputs"],
        "raw_extracted": raw_extracted,
        "metadata": mapped["metadata"],
        "fields_found": len([v for v in raw_extracted.values() if v and v != 0]),
        "fields_missing": fields_missing,
        "extraction_method": "text_input",
        "error": None,
    }
