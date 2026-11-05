"""Check the reference loaders against real files and malformed inputs."""

import json
import os
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from procurement.shared.references import load_company_rules, load_purchase_request


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_CSV = (
    PROJECT_ROOT / "sample-data/engineer/task1-procurement/purchase-request.csv"
)
POLICY_JSON = PROJECT_ROOT / "config/company-rules.json"


class PurchaseRequestTests(unittest.TestCase):
    def test_supplied_csv_loads_all_five_items_with_exact_prices(self):
        items = load_purchase_request()

        self.assertEqual(set(items), {"A", "B", "C", "D", "E"})
        self.assertEqual(items["A"].pr_number, "PR-2026-114")
        self.assertEqual(items["A"].quantity_requested, 12000)
        self.assertEqual(items["A"].description, "Cotton twill fabric, 280 gsm")
        self.assertEqual(items["D"].maximum_unit_price, Decimal("6.50"))
        self.assertIsInstance(items["D"].maximum_unit_price, Decimal)

    def test_csv_also_loads_without_a_byte_order_mark(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "request.csv"
            path.write_text(SAMPLE_CSV.read_text(encoding="utf-8-sig"), encoding="utf-8")

            self.assertEqual(load_purchase_request(path)["B"].quantity_requested, 20000)

    def test_duplicate_item_is_rejected_instead_of_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "request.csv"
            text = SAMPLE_CSV.read_text(encoding="utf-8-sig")
            first_item = text.splitlines()[1]
            path.write_text(text.rstrip() + "\n" + first_item + "\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Duplicate item"):
                load_purchase_request(path)

    def test_missing_header_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "request.csv"
            path.write_text("Item,Quantity requested\nA,12000\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Missing CSV columns"):
                load_purchase_request(path)

    def test_invalid_price_is_not_accepted(self):
        text = SAMPLE_CSV.read_text(encoding="utf-8-sig")
        for invalid_price in ["", "-1", "NaN", "Infinity", "not-a-price"]:
            with self.subTest(price=invalid_price), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "request.csv"
                path.write_text(text.replace("480.00", invalid_price), encoding="utf-8")

                with self.assertRaisesRegex(ValueError, "unit price"):
                    load_purchase_request(path)

    def test_invalid_quantity_is_not_accepted(self):
        text = SAMPLE_CSV.read_text(encoding="utf-8-sig")
        for invalid_quantity in ["", "0", "-1", "1.5"]:
            with self.subTest(quantity=invalid_quantity), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "request.csv"
                path.write_text(text.replace("12000", invalid_quantity), encoding="utf-8")

                with self.assertRaisesRegex(ValueError, "(?i)quantity"):
                    load_purchase_request(path)

    def test_header_only_csv_is_not_a_valid_request(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "request.csv"
            header = SAMPLE_CSV.read_text(encoding="utf-8-sig").splitlines()[0]
            path.write_text(header + "\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "No purchase request items"):
                load_purchase_request(path)

    def test_blank_item_description_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "request.csv"
            text = SAMPLE_CSV.read_text(encoding="utf-8-sig")
            path.write_text(text.replace("Metal zipper, 18 cm", ""), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Description"):
                load_purchase_request(path)


class CompanyRulesTests(unittest.TestCase):
    def test_policy_percentages_use_exact_decimal_values(self):
        rules = load_company_rules()

        self.assertEqual(rules["thresholds"]["minimum_weekly_penalty_percent"], Decimal("0.5"))
        self.assertIsInstance(rules["thresholds"]["maximum_advance_percent"], Decimal)

    def test_missing_threshold_is_reported(self):
        rules = json.loads(POLICY_JSON.read_text(encoding="utf-8"))
        del rules["thresholds"]["maximum_advance_percent"]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "rules.json"
            path.write_text(json.dumps(rules), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "maximum_advance_percent"):
                load_company_rules(path)

    def test_invalid_threshold_is_not_accepted(self):
        for invalid_value in [-1, "twenty", True, None, float("nan"), float("inf")]:
            with self.subTest(value=invalid_value), tempfile.TemporaryDirectory() as folder:
                rules = json.loads(POLICY_JSON.read_text(encoding="utf-8"))
                rules["thresholds"]["maximum_advance_percent"] = invalid_value
                path = Path(folder) / "rules.json"
                path.write_text(json.dumps(rules), encoding="utf-8")

                with self.assertRaisesRegex(ValueError, "maximum_advance_percent"):
                    load_company_rules(path)

    def test_invalid_json_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "rules.json"
            path.write_text("{ broken json", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Invalid policy JSON"):
                load_company_rules(path)

    def test_missing_policy_sections_are_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "rules.json"
            path.write_text("{}", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "thresholds"):
                load_company_rules(path)

    def test_policy_must_be_an_object(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "rules.json"
            path.write_text("[]", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "object"):
                load_company_rules(path)

    def test_invalid_requirement_cannot_silently_disable_a_check(self):
        rules = json.loads(POLICY_JSON.read_text(encoding="utf-8"))
        rules["requirements"]["tin"] = "yes"
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "rules.json"
            path.write_text(json.dumps(rules), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "tin"):
                load_company_rules(path)

    def test_payment_range_cannot_be_reversed(self):
        rules = json.loads(POLICY_JSON.read_text(encoding="utf-8"))
        rules["thresholds"]["minimum_payment_days"] = 90
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "rules.json"
            path.write_text(json.dumps(rules), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "payment"):
                load_company_rules(path)

    def test_wrong_decision_priority_is_reported(self):
        rules = json.loads(POLICY_JSON.read_text(encoding="utf-8"))
        rules["decision_priority"] = ["Approve", "Reject", "Needs a person to check"]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "rules.json"
            path.write_text(json.dumps(rules), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "decision_priority"):
                load_company_rules(path)


class DefaultPathTests(unittest.TestCase):
    def test_default_files_are_found_from_another_working_directory(self):
        original_directory = Path.cwd()
        with tempfile.TemporaryDirectory() as folder:
            try:
                os.chdir(folder)
                self.assertEqual(load_purchase_request()["E"].quantity_requested, 3000)
                self.assertEqual(load_company_rules()["thresholds"]["maximum_delivery_days"], 45)
            finally:
                os.chdir(original_directory)


if __name__ == "__main__":
    unittest.main()
