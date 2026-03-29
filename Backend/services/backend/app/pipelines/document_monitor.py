from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass
class DocumentValidationResult:
    accepted: bool
    document_type: str
    confidence: float
    reason: str


class DocumentMonitor:
    """
    Deterministic validation scaffold.
    Step-6 will extend this with full PDF parsing + marker checks.
    """

    allowed_extensions = {".pdf"}
    max_size_mb = 25

    def validate(
        self,
        file_path: str,
        *,
        expected_type: Literal["cams_statement", "form16", "any"] = "any",
        extracted_text: str = "",
    ) -> DocumentValidationResult:
        path = Path(file_path)
        if not path.exists():
            return DocumentValidationResult(
                accepted=False,
                document_type="unknown",
                confidence=0.0,
                reason="File not found",
            )

        if path.suffix.lower() not in self.allowed_extensions:
            return DocumentValidationResult(
                accepted=False,
                document_type="unknown",
                confidence=0.1,
                reason="Unsupported file type. Only PDF is allowed.",
            )

        file_size_mb = path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.max_size_mb:
            return DocumentValidationResult(
                accepted=False,
                document_type="unknown",
                confidence=0.2,
                reason="File too large. Max 25MB allowed.",
            )

        with path.open("rb") as f:
            header = f.read(5)
        if header != b"%PDF-":
            return DocumentValidationResult(
                accepted=False,
                document_type="unknown",
                confidence=0.1,
                reason="Invalid PDF signature (magic bytes mismatch).",
            )

        text = extracted_text.lower()

        # Filename + marker based deterministic classification.
        lower_name = path.name.lower()
        cams_markers = [
            "consolidated account statement",
            "folio",
            "isin",
            "cams",
            "kfin",
            "mutual fund",
        ]
        form16_markers = [
            "form no. 16",
            "certificate under section 203",
            "part a",
            "part b",
            "tan",
            "pan",
            "traces",
        ]

        cams_score = sum(1 for m in cams_markers if m in text) + (1 if ("cams" in lower_name or "cas" in lower_name) else 0)
        form16_score = sum(1 for m in form16_markers if m in text) + (1 if ("form16" in lower_name or "form_16" in lower_name) else 0)

        # If an expected type is provided and filename hints strongly match, allow with moderate confidence.
        if expected_type == "cams_statement" and ("cams" in lower_name or "cas" in lower_name):
            return DocumentValidationResult(
                accepted=True,
                document_type="cams_statement",
                confidence=max(0.6, min(0.5 + (cams_score * 0.1), 0.9)),
                reason="Expected CAMS statement and filename hints match.",
            )
        if expected_type == "form16" and ("form16" in lower_name or "form_16" in lower_name):
            return DocumentValidationResult(
                accepted=True,
                document_type="form16",
                confidence=max(0.6, min(0.5 + (form16_score * 0.1), 0.9)),
                reason="Expected Form16 and filename hints match.",
            )

        if cams_score >= 2 and cams_score >= form16_score:
            if expected_type not in {"any", "cams_statement"}:
                return DocumentValidationResult(
                    accepted=False,
                    document_type="cams_statement",
                    confidence=0.7,
                    reason="Uploaded document appears to be CAMS/CAS but endpoint expected different type.",
                )
            return DocumentValidationResult(
                accepted=True,
                document_type="cams_statement",
                confidence=min(0.5 + (cams_score * 0.1), 0.95),
                reason="CAMS/CAS markers detected.",
            )
        if form16_score >= 2 and form16_score > cams_score:
            if expected_type not in {"any", "form16"}:
                return DocumentValidationResult(
                    accepted=False,
                    document_type="form16",
                    confidence=0.7,
                    reason="Uploaded document appears to be Form16 but endpoint expected different type.",
                )
            return DocumentValidationResult(
                accepted=True,
                document_type="form16",
                confidence=min(0.5 + (form16_score * 0.1), 0.95),
                reason="Form16 markers detected.",
            )

        return DocumentValidationResult(
            accepted=False,
            document_type="unknown",
            confidence=0.25,
            reason="Could not classify document from deterministic markers.",
        )
