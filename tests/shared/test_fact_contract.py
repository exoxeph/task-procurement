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

    def test_conflicting_reference_fields_are_not_silently_accepted(self):
        fields = {"payment_days": replace(self.field, reference_event="delivery"),
                  "payment_reference": replace(self.field, value="invoice")}
        run = validate_fields(fields, self.document)
        self.assertEqual(run.fields["payment_days"].status, "unrecognized")
        self.assertTrue(run.issues)
