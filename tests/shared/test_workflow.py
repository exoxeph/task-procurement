"""The folder split must preserve complete facts and portable reference loading."""

import json
from contextlib import redirect_stdout
from io import BytesIO, StringIO
from decimal import Decimal
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

from procurement.approach1.extractor import extract_document
from procurement.shared.pdf_text import read_pdf
from procurement.shared.references import (
    SAMPLE_DIRECTORY, load_company_rules, load_purchase_request,
)
from procurement.review import main, review_document
from procurement.shared.extraction import FACT_NAMES


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class WorkflowTests(unittest.TestCase):
    def test_baseline_retains_supplier_financial_and_contract_facts(self):
        path = SAMPLE_DIRECTORY / "supplier-pack-01.pdf"
        fields = extract_document(read_pdf(path)).fields

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

    def test_baseline_does_not_contact_ollama(self):
        with patch('urllib.request.urlopen', side_effect=AssertionError('baseline attempted network access')):
            result = review_document(SAMPLE_DIRECTORY / 'supplier-pack-03.pdf', load_purchase_request(), load_company_rules())
        self.assertEqual(result.verdict, 'Reject')

    def test_both_mode_continues_after_an_ai_failure_and_saves_separate_reports(self):
        chats = []
        empty = dict(value=None, status='not_found', raw_value=None, reference_event=None,
                     conditions=[], minimum_value=None, maximum_value=None, evidence=[])
        payload = {'fields': {name: empty for name in FACT_NAMES}, 'issues': [], 'item_count': 1}
        def local_service(request, timeout):
            if request.full_url.endswith('/chat'):
                chats.append(request)
                if len(chats) == 1:
                    from http.client import BadStatusLine
                    raise BadStatusLine('temporary malformed HTTP response')
                response = {'model': 'qwen2.5:7b', 'done': True, 'done_reason': 'stop',
                            'prompt_eval_count': 1000, 'eval_count': 2000,
                            'message': {'role': 'assistant', 'content': json.dumps(payload)}}
            elif request.full_url.endswith('/version'):
                response = {'version': 'test-version'}
            else:
                response = {'models': []}
            return BytesIO(json.dumps(response).encode())

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'report.html'
            argv = ['review', str(SAMPLE_DIRECTORY / 'supplier-pack-01.pdf'),
                    str(SAMPLE_DIRECTORY / 'supplier-pack-03.pdf'), '--approach', 'both',
                    '--output', str(output), '--artifacts', str(Path(directory) / 'runs')]
            console = StringIO()
            with patch('sys.argv', argv), redirect_stdout(console), patch(
                    'procurement.approach2.extractor.urlopen', side_effect=local_service):
                status = main()
            self.assertEqual(status, 1)
            self.assertEqual(len(chats), 2)
            self.assertTrue(output.with_name('report-approach1.html').is_file())
            ai_html = output.with_name('report-approach2.html').read_text(encoding='utf-8')
            self.assertIn('local Ollama', ai_html)
            self.assertNotIn('This run uses no AI', ai_html)
            self.assertIn('Extraction failures: 1', console.getvalue())
            self.assertEqual(len(list((Path(directory) / 'runs').glob('*.json'))), 4)
            self.assertIn('Procurement extraction comparison', output.read_text(encoding='utf-8'))
            summary = json.loads(output.with_suffix('.json').read_text(encoding='utf-8'))
            self.assertEqual(summary['approach2']['total'], 2)
            self.assertEqual(summary['approach2']['fields']['total'], 54)
            self.assertEqual(summary['approach2']['extraction_failures'], 1)
