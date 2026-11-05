"""Exercise the real reader on supplied PDFs and temporary file-handling fixtures."""

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pymupdf

from procurement.shared.pdf_text import PdfReadError, read_pdf


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DIRECTORY = PROJECT_ROOT / "sample-data/engineer/task1-procurement"
FIRST_PDF = SAMPLE_DIRECTORY / "supplier-pack-01.pdf"
SECOND_PDF = SAMPLE_DIRECTORY / "supplier-pack-02.pdf"


class PdfTextTests(unittest.TestCase):
    def test_first_sample_keeps_document_text_and_source_page(self):
        document = read_pdf(FIRST_PDF)

        self.assertEqual(document.source_path, FIRST_PDF.resolve())
        self.assertEqual(len(document.pages), 1)
        self.assertEqual(document.pages[0].page_number, 1)
        self.assertIn("Padma Textile Mills Ltd", document.pages[0].text)
        self.assertIn("472.00", document.pages[0].text)
        self.assertIn("10% advance payable with the purchase order.", document.pages[0].text)
        self.assertEqual(document.issues, ())

    def test_all_ten_samples_keep_their_supplier_names_and_quotation_numbers(self):
        suppliers = [
            "Padma Textile Mills Ltd", "Jamuna Trims and Accessories",
            "Karnaphuli Yarn Traders", "Surma Packaging Industries",
            "Meghna Carton Works", "Teesta Fabrics Ltd", "Rupsha Zipper Factory",
            "Bhairab Thread and Co", "Dhaleshwari Poly Pack", "Kushiyara Box Industries",
        ]
        for number, supplier in enumerate(suppliers, start=1):
            with self.subTest(pack=number):
                path = SAMPLE_DIRECTORY / f"supplier-pack-{number:02d}.pdf"
                document = read_pdf(path)

                self.assertEqual(len(document.pages), 1)
                self.assertIn(supplier, document.pages[0].text)
                self.assertIn(f"QT-2026-{900 + number}", document.pages[0].text)
                self.assertEqual(document.issues, ())

    def test_multiple_pages_preserve_their_order_and_numbers(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "combined.pdf"
            with pymupdf.open() as combined:
                for source_path in (FIRST_PDF, SECOND_PDF):
                    with pymupdf.open(source_path) as source:
                        combined.insert_pdf(source)
                combined.save(path)

            document = read_pdf(path)

            self.assertEqual([page.page_number for page in document.pages], [1, 2])
            self.assertIn("Padma Textile Mills Ltd", document.pages[0].text)
            self.assertIn("Jamuna Trims and Accessories", document.pages[1].text)
            self.assertEqual(document.issues, ())

    def test_blank_page_is_retained_and_flagged_for_review(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "blank.pdf"
            with pymupdf.open() as blank:
                blank.new_page()
                blank.save(path)

            document = read_pdf(path)

            self.assertEqual(len(document.pages), 1)
            self.assertEqual(document.pages[0].page_number, 1)
            self.assertEqual(document.pages[0].text, "")
            self.assertTrue(any("Page 1" in issue for issue in document.issues))

    def test_blank_middle_page_does_not_shift_later_page_references(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "mixed.pdf"
            with pymupdf.open() as combined:
                with pymupdf.open(FIRST_PDF) as first:
                    combined.insert_pdf(first)
                combined.new_page()
                with pymupdf.open(SECOND_PDF) as second:
                    combined.insert_pdf(second)
                combined.save(path)

            document = read_pdf(path)

            self.assertEqual([page.page_number for page in document.pages], [1, 2, 3])
            self.assertEqual(document.pages[1].text, "")
            self.assertIn("Jamuna Trims and Accessories", document.pages[2].text)
            self.assertTrue(any("Page 2" in issue for issue in document.issues))

    def test_missing_file_has_a_readable_error(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(PdfReadError, "not found"):
                read_pdf(Path(folder) / "missing.pdf")

    def test_empty_and_malformed_files_cannot_pass_as_readable_pdfs(self):
        for contents in (b"", b"%PDF-1.7\nnot a complete PDF"):
            with self.subTest(contents=contents), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "broken.pdf"
                path.write_bytes(contents)

                with self.assertRaises(PdfReadError):
                    read_pdf(path)

    def test_non_pdf_content_is_rejected_even_with_a_pdf_extension(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "not-really.pdf"
            path.write_text("A plain text document.", encoding="utf-8")

            with self.assertRaises(PdfReadError):
                read_pdf(path)

    def test_password_protected_pdf_requires_review(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "encrypted.pdf"
            with pymupdf.open(FIRST_PDF) as source:
                source.save(
                    path,
                    encryption=pymupdf.PDF_ENCRYPT_AES_256,
                    owner_pw="test-owner-password",
                    user_pw="test-reader-password",
                )

            with self.assertRaisesRegex(PdfReadError, "password"):
                read_pdf(path)

    def test_repaired_pdf_is_flagged_instead_of_looking_clean(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "damaged-index.pdf"
            damaged = re.sub(rb"startxref\s+\d+", b"startxref\n0", FIRST_PDF.read_bytes())
            path.write_bytes(damaged)

            document = read_pdf(path)

            self.assertIn("Padma Textile Mills Ltd", document.pages[0].text)
            self.assertTrue(any("repair" in issue.lower() for issue in document.issues))


class PdfPreviewTests(unittest.TestCase):
    def test_preview_prints_page_text(self):
        result = subprocess.run(
            [sys.executable, "-m", "procurement.shared.pdf_text", str(FIRST_PDF)],
            cwd=PROJECT_ROOT, capture_output=True, text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Page 1", result.stdout)
        self.assertIn("Padma Textile Mills Ltd", result.stdout)

    def test_summary_does_not_dump_document_text(self):
        result = subprocess.run(
            [sys.executable, "-m", "procurement.shared.pdf_text", str(FIRST_PDF), "--summary"],
            cwd=PROJECT_ROOT, capture_output=True, text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("supplier-pack-01.pdf", result.stdout)
        self.assertNotIn("Padma Textile Mills Ltd", result.stdout)

    def test_missing_pdf_preview_returns_nonzero_exit_code(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run(
                [sys.executable, "-m", "procurement.shared.pdf_text", str(Path(folder) / "missing.pdf")],
                cwd=PROJECT_ROOT, capture_output=True, text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not found", result.stderr)

    def test_blank_pdf_preview_returns_nonzero_exit_code(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "blank.pdf"
            with pymupdf.open() as blank:
                blank.new_page()
                blank.save(path)
            result = subprocess.run(
                [sys.executable, "-m", "procurement.shared.pdf_text", str(path)],
                cwd=PROJECT_ROOT, capture_output=True, text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Page 1", result.stdout)
        self.assertIn("no selectable text", result.stdout)


if __name__ == "__main__":
    unittest.main()
