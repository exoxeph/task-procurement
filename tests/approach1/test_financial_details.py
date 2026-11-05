"""Check stated financial facts, exact evidence, and unsupported table handling."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pymupdf

from procurement.approach1.financial_details import extract_financial_details
from procurement.shared.pdf_text import PdfDocument, PdfPage, read_pdf
from procurement.shared.table_layout import PdfTable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DIRECTORY = PROJECT_ROOT / "sample-data/engineer/task1-procurement"
FIELD_NAMES = (
    "item_code", "description", "quantity", "unit", "unit_price", "line_amount",
    "subtotal", "vat_rate", "vat_amount", "total", "unit_price_tax_note",
)

# Hand-checked figures as printed, including pack 09's incorrect amount.
EXPECTED = [
    ("A", "Cotton twill fabric, 280 gsm", "12,000", "metre", "472.00", "5,664,000.00", "5,664,000.00", "15", "849,600.00", "6,513,600.00", None),
    ("B", "Metal zipper, 18 cm", "20,000", "piece", "36.00", "720,000.00", "720,000.00", "15", "108,000.00", "828,000.00", None),
    ("C", "Polyester sewing thread, cone", "800", "cone", "229.00", "183,200.00", "183,200.00", "15", "27,480.00", "210,680.00", None),
    ("D", "Poly bag, 30 x 40 cm", "50,000", "piece", "6.65", "332,500.00", "332,500.00", "15", "49,875.00", "382,375.00", None),
    ("E", "Carton box, 5-ply", "3,000", "piece", "92.00", "276,000.00", "276,000.00", "15", "41,400.00", "317,400.00", None),
    ("A", "Cotton twill fabric, 280 gsm", "12,000", "metre", "465.00", "5,580,000.00", "5,580,000.00", "15", "837,000.00", "6,417,000.00", None),
    ("B", "Metal zipper, 18 cm", "16,500", "piece", "35.00", "577,500.00", "577,500.00", "15", "86,625.00", "664,125.00", None),
    ("C", "Polyester sewing thread, cone", "800", "cone", "205.00", "164,000.00", "164,000.00", "15", "24,600.00", "188,600.00", None),
    ("D", "Poly bag, 30 x 40 cm", "50,000", "piece", "6.40", "322,000.00", "322,000.00", "15", "48,300.00", "370,300.00", None),
    ("E", "Carton box, 5-ply", "3,000", "piece", "94.00", "282,000.00", None, None, None, "282,000.00", "VAT included"),
]

TABLE = (
    "Item\nDescription\nQty\nUnit\nUnit price (BDT)\nAmount (BDT)\n"
    "A\nCotton twill fabric, 280 gsm\n12,000\nmetre\n472.00\n5,664,000.00\n"
)
TOTALS = "Subtotal\n5,664,000.00\nVAT 15%\n849,600.00\nTotal\n6,513,600.00\n"


def table_fixture(**changes):
    values=dict(zip(FIELD_NAMES[:6],EXPECTED[0][:6]))
    values.update(changes)
    return PdfTable(('Item','Description','Qty','Unit','Unit price (BDT)','Amount (BDT)'),
                    (tuple(values[name] for name in FIELD_NAMES[:6]),),(0,0,600,100))


def document_from_text(text: str, page_number: int = 1, *, tables=(), outside_text=None) -> PdfDocument:
    # Geometry is explicit fixture input. Production never infers these cells
    # from native text order; actual coordinate extraction has separate PDF tests.
    return PdfDocument(Path("financial-fixture.pdf"), (PdfPage(page_number,text,tables,outside_text),), ())


class FinancialDetailsTests(unittest.TestCase):
    def test_all_ten_packs_match_hand_checked_raw_fields_and_exact_evidence(self):
        for number, values in enumerate(EXPECTED, start=1):
            with self.subTest(pack=number):
                document = read_pdf(SAMPLE_DIRECTORY / f"supplier-pack-{number:02d}.pdf")
                fields = extract_financial_details(document)

                self.assertEqual(set(fields), set(FIELD_NAMES))
                for name, value in zip(FIELD_NAMES, values):
                    self.assertEqual(fields[name].value, value, name)
                    self.assertEqual(fields[name].status, "found" if value is not None else "not_found", name)
                    if value is None:
                        self.assertEqual(fields[name].evidence, (), name)
                    else:
                        self.assertTrue(fields[name].evidence, name)
                        for evidence in fields[name].evidence:
                            page = next(p for p in document.pages if p.page_number == evidence.page_number)
                            self.assertIn(evidence.text, page.text, name)
                            self.assertIn(value, evidence.text, name)

    def test_bad_arithmetic_is_preserved_instead_of_corrected(self):
        document = read_pdf(SAMPLE_DIRECTORY / "supplier-pack-09.pdf")
        fields = extract_financial_details(document)

        self.assertEqual(fields["quantity"].value, "50,000")
        self.assertEqual(fields["unit_price"].value, "6.40")
        self.assertEqual(fields["line_amount"].value, "322,000.00")

    def test_tax_inclusive_pack_does_not_get_an_invented_vat_breakdown(self):
        fields = extract_financial_details(read_pdf(SAMPLE_DIRECTORY / "supplier-pack-10.pdf"))

        self.assertEqual(fields["unit_price_tax_note"].value, "VAT included")
        self.assertIn("all taxes included", fields["total"].evidence[0].text)
        for name in ("subtotal", "vat_rate", "vat_amount"):
            self.assertEqual(fields[name].status, "not_found")

    def test_wrapped_description_keeps_its_original_line_break(self):
        text = (TABLE + TOTALS).replace("Cotton twill fabric, 280 gsm", "Cotton twill fabric,\n280 gsm")
        field = extract_financial_details(document_from_text(text,tables=(table_fixture(description='Cotton twill fabric,\n280 gsm'),),outside_text=TOTALS))["description"]

        self.assertEqual(field.value, "Cotton twill fabric,\n280 gsm")
        self.assertIn(field.value, field.evidence[0].text)

    def test_summary_words_in_descriptions_do_not_end_the_table_or_poison_totals(self):
        for description in (
            "Total protection cotton fabric", "VAT resistant fabric",
            "Subtotal label printing fabric", "Supplier branded cotton fabric",
        ):
            with self.subTest(description=description):
                text = (TABLE + TOTALS).replace("Cotton twill fabric, 280 gsm", description)
                fields = extract_financial_details(document_from_text(text,tables=(table_fixture(description=description),),outside_text=TOTALS))

                self.assertEqual(fields["description"].value, description)
                self.assertTrue(all(fields[name].status == "found" for name in FIELD_NAMES[:6]))
                self.assertEqual(fields["subtotal"].value, "5,664,000.00")
                self.assertEqual(fields["vat_rate"].value, "15")
                self.assertEqual(fields["total"].value, "6,513,600.00")

    def test_blank_lines_and_case_variations_keep_exact_evidence(self):
        text = (TABLE + TOTALS).replace("Description", "DESCRIPTION").replace("\n", "\n\n")
        fields = extract_financial_details(document_from_text(text,page_number=3,tables=(table_fixture(),),outside_text=TOTALS.replace('\n','\n\n')))

        self.assertEqual(fields["unit_price"].value, "472.00")
        self.assertEqual(fields["total"].value, "6,513,600.00")
        for field in fields.values():
            for evidence in field.evidence:
                self.assertEqual(evidence.page_number, 3)
                self.assertIn(evidence.text, text)

    def test_same_line_total_values_are_supported(self):
        text = TABLE + "Subtotal: 5,664,000.00\nVAT 15%: 849,600.00\nTotal: 6,513,600.00\n"
        fields = extract_financial_details(document_from_text(text))

        self.assertEqual(fields["subtotal"].value, "5,664,000.00")
        self.assertEqual(fields["vat_rate"].value, "15")
        self.assertEqual(fields["vat_amount"].value, "849,600.00")
        self.assertEqual(fields["total"].value, "6,513,600.00")

    def test_malformed_number_is_not_partially_extracted(self):
        for replacement in ("12,00", "12,000 pieces", "-12,000", "12.5"):
            with self.subTest(value=replacement):
                text = (TABLE + TOTALS).replace("12,000", replacement)
                fields = extract_financial_details(document_from_text(text,tables=(table_fixture(quantity=replacement),),outside_text=TOTALS))

                self.assertEqual(fields["quantity"].status, "unrecognized")
                self.assertIsNone(fields["quantity"].value)

    def test_malformed_summary_amount_is_not_partially_extracted(self):
        fields = extract_financial_details(document_from_text("Total: 6,51,600.00\n"))

        self.assertEqual(fields["total"].status, "unrecognized")
        self.assertIsNone(fields["total"].value)

    def test_empty_summary_value_is_not_filled_with_another_label(self):
        fields = extract_financial_details(document_from_text("Subtotal\nVAT 15%\nTotal\n"))

        self.assertEqual(fields["subtotal"].status, "unrecognized")
        self.assertEqual(fields["vat_amount"].status, "unrecognized")
        self.assertEqual(fields["total"].status, "unrecognized")

    def test_extra_item_row_is_not_silently_combined_with_the_first(self):
        extra_row = "B\nMetal zipper, 18 cm\n20,000\npiece\n36.00\n720,000.00\n"
        table=table_fixture()
        table=PdfTable(table.headers,table.rows+(('B','Metal zipper, 18 cm','20,000','piece','36.00','720,000.00'),),table.bounds)
        fields = extract_financial_details(document_from_text(TABLE+extra_row+TOTALS,tables=(table,),outside_text=TOTALS))

        for name in FIELD_NAMES[:6]:
            self.assertEqual(fields[name].status, "unrecognized", name)
            self.assertIsNone(fields[name].value, name)

    def test_incomplete_or_unsupported_header_is_not_guessed(self):
        table=table_fixture()
        table=PdfTable(tuple(h.replace('Qty','Something else') for h in table.headers),table.rows,table.bounds)
        fields = extract_financial_details(document_from_text((TABLE+TOTALS).replace('Qty','Something else'),tables=(table,),outside_text=TOTALS))

        self.assertEqual(fields["unit_price"].status, "unrecognized")
        self.assertIsNone(fields["unit_price"].value)

    def test_repeated_identical_tables_and_totals_keep_evidence(self):
        fields = extract_financial_details(document_from_text((TABLE+TOTALS)*2,tables=(table_fixture(),table_fixture()),outside_text=TOTALS*2))

        self.assertEqual(fields["unit_price"].status, "found")
        self.assertEqual(fields["unit_price"].value, "472.00")
        self.assertEqual(len(fields["unit_price"].evidence), 2)
        self.assertEqual(len(fields["total"].evidence), 2)

    def test_conflicting_prices_and_totals_are_ambiguous(self):
        first_page = PdfPage(1,TABLE+TOTALS,(table_fixture(),),TOTALS)
        second_page = PdfPage(2,(TABLE+TOTALS).replace('472.00','473.00').replace('6,513,600.00','6,514,600.00'),
                              (table_fixture(unit_price='473.00'),),TOTALS.replace('6,513,600.00','6,514,600.00'))
        document = PdfDocument(Path("two-pages.pdf"), (first_page, second_page), ())
        fields = extract_financial_details(document)

        for name in ("unit_price", "total"):
            self.assertEqual(fields[name].status, "ambiguous")
            self.assertIsNone(fields[name].value)
            self.assertEqual({e.page_number for e in fields[name].evidence}, {1, 2})

    def test_no_table_does_not_create_item_facts(self):
        fields = extract_financial_details(document_from_text("Some unrelated text.\n"))

        self.assertTrue(all(field.status == "not_found" for field in fields.values()))

    def test_filename_does_not_change_financial_fields(self):
        original = document_from_text(TABLE + TOTALS)
        renamed = PdfDocument(Path("anything-else.pdf"), original.pages, original.issues)

        self.assertEqual(extract_financial_details(original), extract_financial_details(renamed))


class FinancialPreviewTests(unittest.TestCase):
    def test_preview_prints_stated_values_with_evidence(self):
        result = subprocess.run(
            [sys.executable, "-m", "procurement.approach1.financial_details", str(SAMPLE_DIRECTORY / "supplier-pack-09.pdf")],
            cwd=PROJECT_ROOT, capture_output=True, text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("line_amount: 322,000.00", result.stdout)
        self.assertIn("Page 1", result.stdout)

    def test_optional_missing_vat_rows_are_not_a_reader_failure(self):
        result = subprocess.run(
            [sys.executable, "-m", "procurement.approach1.financial_details", str(SAMPLE_DIRECTORY / "supplier-pack-10.pdf")],
            cwd=PROJECT_ROOT, capture_output=True, text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("unit_price_tax_note: VAT included", result.stdout)
        self.assertIn("vat_amount: not_found", result.stdout)

    def test_existing_pdf_issue_still_returns_attention(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "with-blank-page.pdf"
            with pymupdf.open(SAMPLE_DIRECTORY / "supplier-pack-01.pdf") as source:
                source.new_page()
                source.save(path)
            result = subprocess.run(
                [sys.executable, "-m", "procurement.approach1.financial_details", str(path)],
                cwd=PROJECT_ROOT, capture_output=True, text=True,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Page 2 has no selectable text", result.stdout)


if __name__ == "__main__":
    unittest.main()
