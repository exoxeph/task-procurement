"""AI JSON must retain uncertainty and reject malformed responses."""

from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import unittest

from procurement.approach3.schema import parse_response, validate_response
from procurement.shared.extraction import FACT_NAMES
from procurement.shared.pdf_text import PdfDocument, PdfPage
from procurement.approach1.extractor import extract_document
from procurement.shared.pdf_text import read_pdf
from procurement.shared.references import SAMPLE_DIRECTORY


def response_fixture():
    """An explicitly unresolved document, without guessed values."""
    empty = {"value": None, "status": "not_found", "raw_value": None,
             "reference_event": None, "conditions": [], "minimum_value": None,
             "maximum_value": None, "evidence": []}
    return {"fields": {name: deepcopy(empty) for name in FACT_NAMES},
            "issues": [], "item_count": 1}


class SchemaTests(unittest.TestCase):
    def setUp(self):
        self.document = PdfDocument(Path("fixture.pdf"), (PdfPage(1, "Quantity: 12,000"),), ())

    def test_valid_missing_information_is_not_invented(self):
        run = validate_response(response_fixture(), self.document)
        self.assertFalse(run.issues)
        self.assertEqual(set(run.fields), set(FACT_NAMES))
        self.assertTrue(all(field.value is None for field in run.fields.values()))

    def test_root_shape_missing_fields_and_unknown_keys_are_errors(self):
        for mutation in (lambda p: p.pop("fields"),
                         lambda p: p["fields"].pop("tin"),
                         lambda p: p.update(extra="unexpected"),
                         lambda p: p["fields"].update(invented={}),
                         lambda p: p.update(item_count=True),
                         lambda p: p.update(issues="fine")):
            payload = response_fixture()
            mutation(payload)
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                validate_response(payload, self.document)

    def test_invalid_single_fact_does_not_become_a_found_value(self):
        for mutation in (lambda f: f.pop("evidence"), lambda f: f.update(value=12000),
                         lambda f: f.update(status="confident"),
                         lambda f: f.update(conditions="subject to stock"),
                         lambda f: f.update(evidence=[{"page_number": True, "text": "Quantity: 12,000"}]),
                         lambda f: f.update(extra=True)):
            payload = response_fixture()
            mutation(payload["fields"]["quantity"])
            run = validate_response(payload, self.document)
            self.assertEqual(run.fields["quantity"].status, "unrecognized")
            self.assertTrue(run.issues)

    def test_printed_number_and_raw_text_are_preserved(self):
        payload = response_fixture()
        payload["fields"]["quantity"].update(value="12,000", status="found", raw_value="12,000",
            evidence=[{"page_number": 1, "text": "Quantity: 12,000"}])
        field = validate_response(payload, self.document).fields["quantity"]
        self.assertEqual(field.value, "12,000")
        self.assertEqual(field.raw_value, "12,000")

    def test_multiple_items_and_model_reported_issues_require_review(self):
        for count in (0, 2):
            payload = response_fixture()
            payload.update(item_count=count, issues=["Unreadable second table"])
            run = validate_response(payload, self.document)
            self.assertIn("Unreadable second table", run.issues)
            self.assertTrue(any("item" in issue for issue in run.issues))

    def test_multiple_items_cannot_supply_one_confident_selected_quantity(self):
        payload = response_fixture()
        payload['item_count'] = 2
        payload['fields']['quantity'].update(value='12,000', status='found',
            evidence=[{'page_number': 1, 'text': 'Quantity: 12,000'}])
        run = validate_response(payload, self.document)
        self.assertEqual(run.fields['quantity'].status, 'unrecognized')
        self.assertIsNone(run.fields['quantity'].value)

    def test_duplicate_keys_nonfinite_values_and_nonobjects_are_rejected(self):
        for text in ('{"fields": {}, "fields": {}}', '{"value": NaN}', '[]', 'not json'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_response(text, self.document)

    def test_baseline_facts_survive_the_same_json_validation(self):
        document = read_pdf(SAMPLE_DIRECTORY / 'supplier-pack-09.pdf')
        baseline = extract_document(document)
        payload = {"fields": {name: asdict(fact) for name, fact in baseline.fields.items()},
                   "issues": [], "item_count": 1}
        parsed = parse_response(json.dumps(payload), document)
        self.assertFalse(parsed.issues)
        self.assertEqual(parsed.fields, baseline.fields)
        # This is the document's incorrect figure, not a repaired total.
        self.assertEqual(parsed.fields['line_amount'].value, '322,000.00')


class TypedSchemaTests(unittest.TestCase):
    """Approach 3 forces acceptable value formats while the model writes."""

    def resolve(self, node):
        from procurement.approach3.schema import OUTPUT_SCHEMA
        while isinstance(node, dict) and "$ref" in node:
            node = OUTPUT_SCHEMA["$defs"][node["$ref"].rsplit("/", 1)[1]]
        return node

    def properties(self, name):
        from procurement.approach3.schema import OUTPUT_SCHEMA
        shape = self.resolve(OUTPUT_SCHEMA["properties"]["fields"]["properties"][name])
        return {key: self.resolve(node) for key, node in shape["properties"].items()}

    def test_every_fact_is_covered_by_a_shape_the_shared_reader_accepts(self):
        from procurement.approach3.schema import OUTPUT_SCHEMA
        self.assertEqual(set(OUTPUT_SCHEMA["properties"]["fields"]["properties"]), set(FACT_NAMES))
        for name in FACT_NAMES:
            self.assertEqual(set(self.properties(name)),
                             {"value", "status", "raw_value", "reference_event", "conditions",
                              "minimum_value", "maximum_value", "evidence"})

    def test_numeric_value_patterns_reject_the_observed_bad_strings(self):
        import re
        quantity = self.properties("quantity")["value"]["pattern"]
        price = self.properties("unit_price")["value"]["pattern"]
        for bad in ("s800", "S50000", "30 days", "1,200", ""):
            self.assertIsNone(re.fullmatch(quantity, bad), bad)
        for good in ("800", "1200"):
            self.assertTrue(re.fullmatch(quantity, good), good)
        for bad in ("229.00 BDT", "183,200.00", "15%"):
            self.assertIsNone(re.fullmatch(price, bad), bad)
        self.assertTrue(re.fullmatch(price, "183200.00"))

    def test_bounds_and_events_only_exist_on_duration_facts(self):
        self.assertEqual(self.properties("penalty_clause")["minimum_value"], {"type": "null"})
        self.assertEqual(self.properties("quantity")["reference_event"], {"type": "null"})
        duration = self.properties("payment_days")
        self.assertIn("delivery", duration["reference_event"]["enum"])
        self.assertIn("pattern", duration["minimum_value"])

    def test_reference_facts_use_the_same_event_names_as_durations(self):
        for kind in ("payment", "delivery", "validity"):
            self.assertEqual(self.properties(kind + "_reference")["value"]["enum"],
                             self.properties(kind + "_days")["reference_event"]["enum"])

    def test_value_is_written_after_evidence_and_raw_text(self):
        from procurement.approach3.schema import OUTPUT_SCHEMA
        shape = self.resolve(OUTPUT_SCHEMA["properties"]["fields"]["properties"]["quantity"])
        order = list(shape["properties"])
        self.assertLess(order.index("evidence"), order.index("raw_value"))
        self.assertLess(order.index("raw_value"), order.index("value"))
