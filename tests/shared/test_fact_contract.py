"""Reject unsupported facts before they reach either approach's policy checks."""

from dataclasses import replace
from pathlib import Path
import unittest

from procurement.shared.extraction import Evidence, ExtractedField, validate_fields
from procurement.shared.pdf_text import PdfDocument, PdfPage


class FactContractTests(unittest.TestCase):
    def setUp(self):
        self.document = PdfDocument(Path("fixture.pdf"), (
            PdfPage(1, "Payment 45 days after delivery. Penalty: 1% per week."),
        ), ())
        self.field = ExtractedField("45", "found", (
            Evidence(1, "Payment 45 days after delivery."),
        ))

    def test_original_exact_evidence_is_required(self):
        for evidence in ((), (Evidence(2, "Payment 45 days after delivery."),),
                         (Evidence(True, "Payment 45 days after delivery."),),
                         (Evidence(1, "Payment 45 days after invoice."),),
                         (Evidence(1, ""),)):
            with self.subTest(evidence=evidence):
                run = validate_fields({"payment_days": replace(self.field, evidence=evidence)}, self.document)
                self.assertEqual(run.fields["payment_days"].status, "unrecognized")
                self.assertIsNone(run.fields["payment_days"].value)
                self.assertTrue(run.issues)

    def test_valid_excerpt_does_not_prove_semantic_correctness(self):
        # This deliberately incorrect interpretation still cites real source.
        field = replace(self.field, value="50", reference_event="delivery")
        run = validate_fields({"payment_days": field}, self.document)
        self.assertEqual(run.fields["payment_days"].value, "50")

    def test_unsupported_numbers_and_statuses_are_invalidated(self):
        for value in ("NaN", "Infinity", "-1", "1000000000000", "0.0000001", "1,2", "1.5"):
            with self.subTest(value=value):
                run = validate_fields({"payment_days": replace(self.field, value=value)}, self.document)
                self.assertEqual(run.fields["payment_days"].status, "unrecognized")
        for field in (replace(self.field, status="certain"), replace(self.field, value=None),
                      replace(self.field, status="not_found")):
            self.assertEqual(validate_fields({"payment_days": field}, self.document)
                             .fields["payment_days"].status, "unrecognized")

    def test_conflicting_bounds_are_invalid_but_a_range_is_preserved(self):
        field = replace(self.field, value=None, status="ambiguous", minimum_value="28", maximum_value="42")
        parsed = validate_fields({"delivery_days": field}, self.document).fields["delivery_days"]
        self.assertEqual((parsed.minimum_value, parsed.maximum_value), ("28", "42"))
        invalid = replace(field, minimum_value="43")
        self.assertEqual(validate_fields({"delivery_days": invalid}, self.document)
                         .fields["delivery_days"].status, "unrecognized")

    def test_missing_fields_remain_unknown_and_absence_needs_explicit_evidence(self):
        run = validate_fields({"penalty_clause": replace(self.field, value="absent")}, self.document)
        self.assertEqual(run.fields["penalty_clause"].status, "unrecognized")
        self.assertEqual(run.fields["supplier_name"].status, "not_found")
        self.assertIsNone(run.fields["supplier_name"].value)

    def test_whitespace_only_differences_in_a_quote_are_accepted_and_repaired_to_page_text(self):
        document = PdfDocument(Path("fixture.pdf"), (PdfPage(1, "Balance within 40 days\nof delivery."),), ())
        field = replace(self.field, value="40", evidence=(Evidence(1, "Balance within 40 days of delivery."),))
        parsed = validate_fields({"payment_days": field}, document).fields["payment_days"]
        self.assertEqual(parsed.status, "found")
        self.assertEqual(parsed.evidence[0].text, "Balance within 40 days\nof delivery.")  # exact page text

    def test_changed_words_or_numbers_in_a_quote_are_still_refused(self):
        for quote in ("Payment 54 days after delivery.", "Payment 45 days after invoice.", "purchase_order"):
            field = replace(self.field, evidence=(Evidence(1, quote),))
            with self.subTest(quote=quote):
                parsed = validate_fields({"payment_days": field}, self.document).fields["payment_days"]
                self.assertEqual(parsed.status, "unrecognized")

    def test_one_bad_quote_is_dropped_when_another_quote_is_real(self):
        field = replace(self.field, evidence=(Evidence(1, "Payment 45 days after delivery."),
                                              Evidence(1, "an invented sentence")))
        run = validate_fields({"payment_days": field}, self.document)
        self.assertEqual(run.fields["payment_days"].status, "found")
        self.assertEqual([e.text for e in run.fields["payment_days"].evidence],
                         ["Payment 45 days after delivery."])
        self.assertFalse(run.issues)

    def test_unit_marker_is_removed_only_when_the_printed_text_has_that_number(self):
        for name, value, raw, expected in (("vat_rate", "15%", "15%", "15"),
                                           ("advance_percent", "10 %", "10% advance", "10"),
                                           ("payment_days", "30 days", "30 days", "30")):
            with self.subTest(name=name):
                field = replace(self.field, value=value, raw_value=raw)
                parsed = validate_fields({name: field}, self.document).fields[name]
                self.assertEqual((parsed.status, parsed.value, parsed.raw_value), ("found", expected, raw))
        for name, value, raw in (("advance_percent", "0%", "No advance payment required"),
                                 ("advance_percent", "1%", "10% advance"),
                                 ("quantity", "5%", "5%"), ("vat_rate", "15%", None)):
            with self.subTest(name=name, value=value, raw=raw):
                field = replace(self.field, value=value, raw_value=raw)
                self.assertEqual(validate_fields({name: field}, self.document).fields[name].status, "unrecognized")

    def test_conflicting_reference_fields_are_not_silently_accepted(self):
        fields = {"payment_days": replace(self.field, reference_event="delivery"),
                  "payment_reference": replace(self.field, value="invoice")}
        run = validate_fields(fields, self.document)
        self.assertEqual(run.fields["payment_days"].status, "unrecognized")
        self.assertTrue(run.issues)
