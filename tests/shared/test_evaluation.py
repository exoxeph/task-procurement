"""Failed sample attempts must not disappear from reported accuracy."""

from dataclasses import replace
import unittest

from procurement.review import review_document
from procurement.shared.evaluation import evaluate_samples
from procurement.shared.references import SAMPLE_DIRECTORY, load_company_rules, load_purchase_request


class EvaluationTests(unittest.TestCase):
    def test_nine_results_and_one_input_failure_are_ten_attempts(self):
        paths = sorted(SAMPLE_DIRECTORY.glob('supplier-pack-*.pdf'))
        results = [review_document(path, load_purchase_request(), load_company_rules()) for path in paths[:9]]
        evaluation = evaluate_samples(results, [(str(paths[9]), 'cannot read PDF')])
        self.assertEqual(evaluation['total'], 10)
        self.assertEqual(evaluation['input_failures'], 1)
        self.assertFalse(evaluation['rows'][-1]['verdict_match'])
        self.assertFalse(evaluation['rows'][-1]['rule_match'])

    def test_same_basename_upload_is_not_a_supplied_sample(self):
        result = review_document(SAMPLE_DIRECTORY / 'supplier-pack-01.pdf', load_purchase_request(), load_company_rules())
        document = replace(result.document, source_path=result.document.source_path.parent.parent / 'supplier-pack-01.pdf')
        self.assertEqual(evaluate_samples([replace(result, document=document)])['total'], 0)

    def test_total_ai_failure_is_not_scored_as_a_correct_review_verdict(self):
        result = review_document(SAMPLE_DIRECTORY / 'supplier-pack-04.pdf', load_purchase_request(), load_company_rules())
        run = replace(result.extraction_run, metadata={**result.extraction_run.metadata, 'status': 'failed'})
        evaluation = evaluate_samples([replace(result, extraction_run=run)])
        self.assertEqual(evaluation['total'], 1)
        self.assertEqual(evaluation['extraction_failures'], 1)
        self.assertEqual(evaluation['verdict_matches'], 0)
        self.assertEqual(evaluation['rule_matches'], 0)
