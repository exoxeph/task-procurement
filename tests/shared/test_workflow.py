"""The folder split must preserve complete facts and portable reference loading."""

import json
from decimal import Decimal
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from procurement.approach1.extractor import extract_document
from procurement.shared.pdf_text import read_pdf
from procurement.shared.references import (
    SAMPLE_DIRECTORY, load_company_rules, load_purchase_request,
)
from procurement.review import review_document


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class WorkflowTests(unittest.TestCase):
    def test_baseline_retains_supplier_financial_and_contract_facts(self):
        path = SAMPLE_DIRECTORY / "supplier-pack-01.pdf"
        fields = extract_document(read_pdf(path))

        self.assertEqual(fields["supplier_name"].value, "Padma Textile Mills Ltd")
        self.assertEqual(fields["item_code"].value, "A")
        self.assertEqual(fields["quantity"].value, "12,000")
        self.assertEqual(fields["unit_price"].value, "472.00")
        self.assertEqual(fields["total"].value, "6,513,600.00")
        self.assertEqual(fields["payment_days"].status, "unrecognized")

        result = review_document(path, load_purchase_request(), load_company_rules())
        self.assertEqual(result.fields, fields)
        self.assertEqual(result.verdict, "Needs a person to check")
        self.assertEqual({finding.code for finding in result.findings}, {"payment"})

    def test_default_references_load_outside_the_project_directory(self):
        script = (
            "import json, sys; "
            "sys.path.insert(0, sys.argv[1]); "
            "from procurement.shared.references import load_purchase_request, load_company_rules; "
            "items = load_purchase_request(); policy = load_company_rules(); "
            "print(json.dumps({'quantity': items['A'].quantity_requested, "
            "'maximum_advance': str(policy['thresholds']['maximum_advance_percent'])}))"
        )
        with tempfile.TemporaryDirectory() as directory:
            completed = subprocess.run(
                [sys.executable, "-c", script, str(PROJECT_ROOT)],
                cwd=directory, capture_output=True, text=True,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        references = json.loads(completed.stdout)
        self.assertEqual(references["quantity"], 12000)
        self.assertEqual(Decimal(references["maximum_advance"]), Decimal("20"))
