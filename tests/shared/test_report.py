"""The runnable batch demo, evidence report, and disclosed sample evaluation."""

import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from procurement.shared.evaluation import evaluate_samples
from procurement.shared.references import load_company_rules, load_purchase_request, SAMPLE_DIRECTORY
from procurement.shared.report import render_report
from procurement.review import review_document

ROOT = Path(__file__).resolve().parents[2]


class ReportTests(unittest.TestCase):
    def test_actual_results_preserve_gold_labels_and_report_escalations(self):
        results = [review_document(path, load_purchase_request(), load_company_rules())
                   for path in sorted(SAMPLE_DIRECTORY.glob('supplier-pack-*.pdf'))]
        evaluation = evaluate_samples(results)
        self.assertEqual(evaluation['total'], 10)
        self.assertEqual(evaluation['verdict_matches'],6)
        self.assertEqual(evaluation['rule_matches'],6,evaluation)
        self.assertEqual(evaluation['automatic_decisions'],3)
        self.assertEqual(evaluation['conservative_escalations'],4)
        self.assertEqual(evaluation['unsafe_approvals'],0)
        self.assertEqual(evaluation['incorrect_automatic_decisions'],0)
        self.assertEqual(evaluation['rows'][0]['expected'],'Approve')

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
            self.assertIn('Verdicts: 6/10',result.stdout)
            self.assertIn('Rule sets: 6/10',result.stdout)
            self.assertIn('Automatic decisions: 3/10',result.stdout)
            self.assertIn('development', output.read_text(encoding='utf-8'))

    def test_evaluation_counts_a_wrong_rule_even_when_verdict_is_right(self):
        result = review_document(SAMPLE_DIRECTORY / 'supplier-pack-09.pdf', load_purchase_request(), load_company_rules())
        result = replace(result, findings=())
        evaluation = evaluate_samples([result])
        self.assertEqual(evaluation['verdict_matches'], 1)
        self.assertEqual(evaluation['rule_matches'], 0)

    def test_strict_label_check_reports_mismatches_as_nonzero(self):
        with tempfile.TemporaryDirectory() as directory:
            result=subprocess.run([sys.executable,'-m','procurement.review','--check-labels','--output',str(Path(directory)/'report.html')],
                                  cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(result.returncode,1,result.stderr)

    def test_metrics_count_a_wrong_approval_as_unsafe(self):
        result=review_document(SAMPLE_DIRECTORY/'supplier-pack-03.pdf',load_purchase_request(),load_company_rules())
        evaluation=evaluate_samples([replace(result,verdict='Approve')])
        self.assertEqual(evaluation['unsafe_approvals'],1)
        self.assertEqual(evaluation['incorrect_automatic_decisions'],1)

    def test_report_preserves_term_conditions_references_and_ranges(self):
        result = review_document(SAMPLE_DIRECTORY / 'supplier-pack-01.pdf', load_purchase_request(), load_company_rules())
        field = replace(result.fields['delivery_days'], raw_value='four to six weeks',
                        minimum_value='28', maximum_value='42', conditions=('<acceptance required>',))
        result = replace(result, fields={**result.fields, 'delivery_days': field})
        html = render_report([result], [])
        self.assertIn('four to six weeks', html)
        self.assertIn('purchase_order', html)
        self.assertIn('28', html)
        self.assertIn('42', html)
        self.assertIn('&lt;acceptance required&gt;', html)
        self.assertNotIn('<acceptance required>', html)


if __name__ == '__main__':
    unittest.main()
