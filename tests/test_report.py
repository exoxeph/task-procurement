"""The runnable batch demo, evidence report, and disclosed sample evaluation."""

import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from procurement.evaluation import evaluate_samples
from procurement.references import load_company_rules, load_purchase_request, SAMPLE_DIRECTORY
from procurement.report import render_report
from procurement.review import review_document

ROOT = Path(__file__).resolve().parents[1]


class ReportTests(unittest.TestCase):
    def test_all_ten_match_manual_verdicts_and_rule_codes(self):
        results = [review_document(path, load_purchase_request(), load_company_rules())
                   for path in sorted(SAMPLE_DIRECTORY.glob('supplier-pack-*.pdf'))]
        evaluation = evaluate_samples(results)
        self.assertEqual(evaluation['total'], 10)
        self.assertEqual(evaluation['verdict_matches'], 10)
        self.assertEqual(evaluation['rule_matches'], 10, evaluation)

    def test_report_contains_exact_evidence_and_escapes_untrusted_text(self):
        result = review_document(SAMPLE_DIRECTORY / 'supplier-pack-09.pdf', load_purchase_request(), load_company_rules())
        finding = replace(result.findings[0], reason='<script>alert("x")</script>')
        result = replace(result, findings=(finding,) + result.findings[1:])
        html = render_report([result], [('missing.pdf','<bad input>')])
        self.assertIn('322,000.00', html)
        self.assertIn('Page 1', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;bad input&gt;', html)
        self.assertIn('Needs a person to check', html)

    def test_cli_mixed_good_bad_inputs_keeps_good_result_and_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'report.html'
            command = [sys.executable,'-m','procurement.review',str(SAMPLE_DIRECTORY / 'supplier-pack-01.pdf'),
                       str(Path(directory) / 'missing.pdf'),'--output',str(output)]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn('Padma Textile Mills', output.read_text(encoding='utf-8'))
            self.assertIn('missing.pdf', output.read_text(encoding='utf-8'))

    def test_default_batch_writes_report_and_prints_development_results(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'report.html'
            result = subprocess.run([sys.executable,'-m','procurement.review','--output',str(output)],
                                    cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Verdicts: 10/10', result.stdout)
            self.assertIn('Rule sets: 10/10', result.stdout)
            self.assertIn('development', output.read_text(encoding='utf-8'))

    def test_evaluation_counts_a_wrong_rule_even_when_verdict_is_right(self):
        result = review_document(SAMPLE_DIRECTORY / 'supplier-pack-09.pdf', load_purchase_request(), load_company_rules())
        result = replace(result, findings=())
        evaluation = evaluate_samples([result])
        self.assertEqual(evaluation['verdict_matches'], 1)
        self.assertEqual(evaluation['rule_matches'], 0)


if __name__ == '__main__':
    unittest.main()
