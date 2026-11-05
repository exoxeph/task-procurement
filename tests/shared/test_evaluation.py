"""Failed sample attempts must not disappear from reported accuracy."""

from dataclasses import replace
import hashlib
import unittest

from procurement.review import review_document
from procurement.shared.evaluation import evaluate_samples, evaluate_fields
from procurement.shared.extraction import Evidence, ExtractedField
from procurement.shared.references import SAMPLE_DIRECTORY, load_company_rules, load_purchase_request


class EvaluationTests(unittest.TestCase):
    def example(self, number=1):
        return review_document(SAMPLE_DIRECTORY / f'supplier-pack-{number:02}.pdf',
                               load_purchase_request(), load_company_rules())

    def facts(self, result):
        return {'documents': {result.document.source_path.name: {
            'document_sha256': hashlib.sha256(result.document.source_path.read_bytes()).hexdigest(),
            'facts': {'quantity': {'value': '12000', 'statuses': ['found'], 'reference_event': None,
                                    'minimum_value': None, 'maximum_value': None,
                                    'conditions': [[]], 'disputed': False}}}}}

    def test_wrong_decisions_confusion_and_usage_are_reported(self):
        first, third = self.example(1), self.example(3)
        run = replace(first.extraction_run, metadata={**first.extraction_run.metadata,
                      'elapsed_seconds': 2.5, 'usage': {'prompt_eval_count': 100, 'eval_count': 200}})
        evaluation = evaluate_samples([replace(first, verdict='Reject', extraction_run=run),
                                       replace(third, verdict='Approve')])
        self.assertEqual(evaluation['wrong_rejections'], 1)
        self.assertEqual(evaluation['unsafe_approvals'], 1)
        self.assertEqual(evaluation['confusion']['Approve']['Reject'], 1)
        self.assertEqual(evaluation['confusion']['Reject']['Approve'], 1)
        self.assertEqual(evaluation['prompt_tokens'], 100)
        self.assertEqual(evaluation['output_tokens'], 200)
        self.assertGreaterEqual(evaluation['elapsed_seconds'], 2.5)

    def test_field_denominator_includes_unresolved_and_failed_inputs(self):
        result = self.example()
        labels = self.facts(result)
        fields = {**result.fields, 'quantity': ExtractedField(None, 'not_found', ())}
        measured = evaluate_fields([replace(result, fields=fields)], labels)
        self.assertEqual((measured['matches'], measured['total']), (0, 1))
        failed = evaluate_fields([], labels, [(str(result.document.source_path), 'unreadable')])
        self.assertEqual((failed['matches'], failed['total']), (0, 1))

    def test_numeric_normalization_and_disputed_facts(self):
        result = self.example()
        labels = self.facts(result)
        measured = evaluate_fields([result], labels)
        self.assertEqual((measured['matches'], measured['total']), (1, 1))
        self.assertEqual(measured['by_field']['quantity'], {'matches': 1, 'total': 1})
        labels['documents'][result.document.source_path.name]['facts']['quantity']['disputed'] = True
        disputed = evaluate_fields([result], labels)
        self.assertEqual((disputed['total'], disputed['disputed']), (0, 1))

    def test_conditions_reference_and_range_are_part_of_fact_accuracy(self):
        result = self.example()
        labels = self.facts(result)
        labels['documents'][result.document.source_path.name]['facts'] = {
            'payment_days': {'value': '45', 'statuses': ['found'], 'reference_event': 'delivery',
                             'minimum_value': '45', 'maximum_value': '45',
                             'conditions': [['acceptance of goods']], 'disputed': False}}
        fact = ExtractedField('45', 'found', (Evidence(1, result.document.pages[0].text),),
                              reference_event='delivery', conditions=('acceptance of goods',))
        for change, expected in (({}, 1), ({'conditions': ()}, 0),
                                  ({'reference_event': 'invoice'}, 0),
                                  ({'minimum_value': '30', 'maximum_value': '60'}, 0)):
            updated = replace(result, fields={**result.fields, 'payment_days': replace(fact, **change)})
            self.assertEqual(evaluate_fields([updated], labels)['matches'], expected)

    def test_fields_exclude_assisted_and_same_name_uploads(self):
        result = self.example()
        labels = self.facts(result)
        assisted = replace(result.extraction_run, metadata={**result.extraction_run.metadata, 'assisted': True})
        self.assertEqual(evaluate_fields([replace(result, extraction_run=assisted)], labels)['total'], 0)
        upload = replace(result.document, source_path=result.document.source_path.parent.parent / result.document.source_path.name)
        self.assertEqual(evaluate_fields([replace(result, document=upload)], labels)['total'], 0)

    def test_reference_fact_can_repeat_its_event_as_metadata(self):
        result = self.example()
        labels = self.facts(result)
        labels['documents'][result.document.source_path.name]['facts'] = {
            'delivery_reference': {'value': 'purchase_order', 'statuses': ['found'],
                                   'reference_event': None, 'minimum_value': None, 'maximum_value': None,
                                   'conditions': [[]], 'disputed': False}}
        fact = replace(result.fields['delivery_reference'], reference_event='purchase_order')
        updated = replace(result, fields={**result.fields, 'delivery_reference': fact})
        self.assertEqual(evaluate_fields([updated], labels)['matches'], 1)

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
