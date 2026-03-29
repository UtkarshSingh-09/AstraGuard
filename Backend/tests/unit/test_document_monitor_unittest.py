import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = ROOT / "services" / "backend"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from app.pipelines.document_monitor import DocumentMonitor  # noqa: E402


class DocumentMonitorTests(unittest.TestCase):
    def setUp(self):
        self.monitor = DocumentMonitor()

    def _make_pdf(self, name: str) -> str:
        tmp_dir = Path(tempfile.mkdtemp())
        f = tmp_dir / name
        f.write_bytes(b"%PDF-1.4\n%mock-pdf")
        return str(f)

    def test_rejects_non_pdf_signature(self):
        tmp_dir = Path(tempfile.mkdtemp())
        f = tmp_dir / "test.pdf"
        f.write_text("not-pdf")
        result = self.monitor.validate(str(f))
        self.assertFalse(result.accepted)

    def test_detects_cams_markers(self):
        path = self._make_pdf("cams_statement.pdf")
        text = "Consolidated Account Statement folio mutual fund CAMS ISIN"
        result = self.monitor.validate(path, expected_type="cams_statement", extracted_text=text)
        self.assertTrue(result.accepted)
        self.assertEqual(result.document_type, "cams_statement")

    def test_detects_form16_markers(self):
        path = self._make_pdf("form16.pdf")
        text = "Form No. 16 certificate under section 203 TAN PAN Part A Part B"
        result = self.monitor.validate(path, expected_type="form16", extracted_text=text)
        self.assertTrue(result.accepted)
        self.assertEqual(result.document_type, "form16")

    def test_expected_cams_with_filename_hint(self):
        path = self._make_pdf("cas_mailback_statement.pdf")
        result = self.monitor.validate(path, expected_type="cams_statement", extracted_text="")
        self.assertTrue(result.accepted)
        self.assertEqual(result.document_type, "cams_statement")


if __name__ == "__main__":
    unittest.main()
