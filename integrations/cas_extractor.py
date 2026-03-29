"""
CAMS/KFintech CAS Extractor — extracts mutual fund portfolio data using casparser.

Approach:
1. Uses the open-source `casparser` library to securely decrypt and parse CAS PDFs.
2. Extracts Folios, Schemes, Units, NAV, Current Valuation, and Transactions.
3. Maps it directly into our Portfolio Engine input format.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("astraguard.integrations.cas_extractor")

# ═══════════════════════════════════════════════════════════════════════
# MONKEY-PATCH: casparser 0.8.x + Pydantic v2 compatibility fix
# casparser's PartialCASData model requires investor_info to be non-None,
# but some CAS PDFs (especially older CAMS formats) don't have extractable
# investor info in the header. This patch makes the field Optional.
# ═══════════════════════════════════════════════════════════════════════
try:
    import casparser.types as _ct
    _OrigPartialCAS = _ct.PartialCASData

    class _PatchedPartialCASData(_OrigPartialCAS):  # type: ignore[valid-type]
        investor_info: Optional[_ct.InvestorInfo] = None
        model_config = {"arbitrary_types_allowed": True}

    _ct.PartialCASData = _PatchedPartialCASData  # type: ignore[misc]
    # Also patch in the mupdf parser module which has its own import reference
    import casparser.parsers.mupdf as _mupdf_mod
    _mupdf_mod.PartialCASData = _PatchedPartialCASData  # type: ignore[attr-defined]
    logger.info("casparser PartialCASData patched for Pydantic v2 compatibility")
except Exception as _patch_err:
    logger.warning(f"casparser monkey-patch skipped: {_patch_err}")

import casparser


async def extract_from_cas(pdf_path: str | Path, password: str) -> Dict[str, Any]:
    """
    Extracts portfolio data from a Consolidated Account Statement (CAS) PDF.

    Args:
        pdf_path: Path to the CAS PDF file.
        password: The document password (usually PAN in ALL CAPS or custom).

    Returns:
        dict containing success status, raw CAS JSON, and mapped portfolio data.
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        return {"success": False, "error": f"File not found: {pdf_path}"}
    if pdf_path.suffix.lower() != ".pdf":
        return {"success": False, "error": "File must be a PDF"}

    try:
        # Step 1: Parse the CAS PDF
        # casparser handles both CAMS and KFintech layouts automatically
        cas_data_obj = casparser.read_cas_pdf(str(pdf_path), password)
        # Convert Pydantic object to dict for safe .get() calls
        cas_data = cas_data_obj.model_dump() if hasattr(cas_data_obj, "model_dump") else (cas_data_obj.dict() if hasattr(cas_data_obj, "dict") else cas_data_obj)
        
        # Determine the total valuation to map it to our internal DNA/Portfolio structures
        total_valuation = 0.0
        mapped_funds = []

        # Iterate through folios and schemes
        for folio in cas_data.get("folios", []):
            for scheme in folio.get("schemes", []):
                val = scheme.get("valuation", {}) or {}
                current_value = float(val.get("value", 0.0) or 0.0)
                nav = float(val.get("nav", 0.0) or 0.0)
                # balance can be None in some CAS formats — fall back to computing from value/nav
                units = scheme.get("balance")
                if units is None or units == 0:
                    units = (current_value / nav) if nav > 0 else 0.0
                units = float(units)
                
                if current_value > 0:
                    total_valuation += current_value
                    mapped_funds.append({
                        "fund_name": scheme.get("scheme"),
                        "folio_number": folio.get("folio"),
                        "amc": folio.get("amc"),
                        "current_value": current_value,
                        "units": units,
                        "nav": nav,
                        "nav_date": str(val.get("date", "")),
                        "isin": scheme.get("isin"),
                        "amfi_code": scheme.get("amfi")
                    })

        # Safely extract investor info (may be None after our patch)
        investor_info = cas_data.get("investor_info") or {}

        return {
            "success": True,
            "portfolio_summary": {
                "total_valuation": total_valuation,
                "fund_count": len(mapped_funds),
                "investor_name": investor_info.get("name") if isinstance(investor_info, dict) else None,
                "email": investor_info.get("email") if isinstance(investor_info, dict) else None,
                "mobile": investor_info.get("mobile") if isinstance(investor_info, dict) else None,
                "statement_period": cas_data.get("statement_period", {})
            },
            "funds": mapped_funds,
            "raw_cas_data": cas_data,  # For debugging or deep transaction analysis
        }

    except casparser.exceptions.IncorrectPasswordError:
        return {"success": False, "error": "Incorrect password. CAS PDFs are usually encrypted with your PAN (ALL CAPS)."}
    except Exception as e:
        logger.error(f"Failed to parse CAS: {e}")
        return {"success": False, "error": f"Failed to parse CAS statement: {str(e)}"}
