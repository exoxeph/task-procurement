"""Corrections must be attributable, source-backed and separate from AI scores."""

from copy import deepcopy
from dataclasses import asdict, replace
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from procurement.review import review_document
from procurement.shared.evaluation import evaluate_samples
from procurement.shared.human_review import apply_corrections, build_questions
from procurement.shared.references import SAMPLE_DIRECTORY, load_company_rules, load_purchase_request
from procurement.shared.report import render_report
from procurement.shared.runs import write_run


class HumanReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = SAMPLE_DIRECTORY / 'supplier-pack-09.pdf'
        cls.result = review_document(cls.path, load_purchase_request(), load_company_rules())

    def response(self):
        run = self.result.extraction_run
        return {'source_run_id': run.metadata['run_id'],
                'document_sha256': run.metadata['document_sha256'],
                'reviewer': 'Example reviewer', 'reviewed_at': '2026-11-05T15:00:00+06:00',
                'reason': 'Checked the printed amount against page 1.',
                'corrections': {'line_amount': json.loads(json.dumps(asdict(run.fields['line_amount'])))}}

    def test_requires_identity_audit_and_exact_response_keys(self):
        for key in ('source_run_id', 'document_sha256', 'reviewer', 'reviewed_at', 'reason'):
            for value in (None, '', '   '):
                response = self.response()
                response[key] = value
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    apply_corrections(self.result.extraction_run, self.result.document, response)
        for key, value in (('source_run_id', 'another-run'), ('document_sha256', '0' * 64),
                           ('reviewed_at', '2026-11-05T15:00:00'), ('reviewed_at', 'tomorrow'),
                           ('verdict', 'Approve'), ('thresholds', {'payment_days': 999})):
            response = self.response()
            response[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                apply_corrections(self.result.extraction_run, self.result.document, response)

    def test_rejects_unknown_fields_bad_types_and_invented_evidence(self):
        for correction in ({}, {'verdict': 'Approve'}, {'total': {}},
                           {'total': {**self.response()['corrections']['line_amount'], 'value': 100}},
                           {'total': {**self.response()['corrections']['line_amount'],
                                      'evidence': [{'page_number': 1, 'text': 'invented amount'}]}}):
            response = self.response()
            response['corrections'] = correction
            with self.subTest(correction=correction), self.assertRaises(ValueError):
                apply_corrections(self.result.extraction_run, self.result.document, response)

    def test_new_run_preserves_original_and_raw_answer(self):
        original = replace(self.result.extraction_run, raw_response='original AI answer')
        before = deepcopy(original)
        assisted = apply_corrections(original, self.result.document, self.response())
        self.assertEqual(original, before)
        self.assertIsNot(assisted.fields, original.fields)
        self.assertNotEqual(assisted.metadata['run_id'], original.metadata['run_id'])
        self.assertTrue(assisted.metadata['assisted'])
        self.assertEqual(assisted.metadata['source_run_id'], original.metadata['run_id'])
        self.assertEqual(assisted.metadata['human_review']['reviewer'], 'Example reviewer')
        self.assertEqual(assisted.raw_response, 'original AI answer')
        evaluation = evaluate_samples([self.result, replace(self.result, extraction_run=assisted)])
        self.assertEqual(evaluation['total'], 1)
        self.assertEqual(evaluation['assisted_excluded'], 1)

    def test_questions_have_evidence_and_do_not_appear_for_final_decisions(self):
        questions = build_questions(self.result)
        self.assertTrue(questions)
        self.assertTrue(all(q['question'] and q['evidence'] for q in questions))
        self.assertTrue(any(q['code'] == 'line_arithmetic' for q in questions))
        arithmetic = next(q for q in questions if q['code'] == 'line_arithmetic')
        self.assertEqual(arithmetic['fields'], ['quantity', 'unit_price', 'line_amount'])
        self.assertEqual(build_questions(replace(self.result, verdict='Reject')), [])
        self.assertEqual(build_questions(replace(self.result, verdict='Approve')), [])

    def test_report_shows_stages_pending_questions_and_escaped_audit(self):
        self.assertEqual(len(self.result.steps), 5)
        self.assertEqual(self.result.steps[-1]['status'], 'needs_review')
        self.assertIn('Human review questions', render_report([self.result], []))
        response = self.response()
        response['reviewer'] = '<script>name</script>'
        assisted = apply_corrections(self.result.extraction_run, self.result.document, response)
        html = render_report([replace(self.result, extraction_run=assisted)], [])
        self.assertIn('&lt;script&gt;name&lt;/script&gt;', html)
        self.assertNotIn('<script>', html)
        self.assertIn('source run id', html)

    def test_cli_rechecks_saved_run_without_ai_and_does_not_overwrite_it(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            source = write_run(self.result.extraction_run, self.result.document, directory)
            before = source.read_bytes()
            response = directory / 'response.json'
            response.write_text(json.dumps(self.response()), encoding='utf-8')
            output = directory / 'assisted.html'
            command = [sys.executable, '-m', 'procurement.review', str(self.path),
                       '--source-run', str(source), '--review-response', str(response),
                       '--artifacts', str(directory / 'assisted'), '--output', str(output)]
            completed = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(source.read_bytes(), before)
            saved = list((directory / 'assisted').glob('*.json'))
            self.assertEqual(len(saved), 1)
            payload = json.loads(saved[0].read_text(encoding='utf-8'))
            self.assertTrue(payload['metadata']['assisted'])
            self.assertIn('line_arithmetic', output.read_text(encoding='utf-8'))
            self.assertIn('Needs a person to check', completed.stdout)
            self.assertIn('Assisted runs excluded: 1', completed.stdout)
            for extra in ([str(self.path)], ['--approach', 'both']):
                invalid = subprocess.run(command + extra, capture_output=True, text=True)
                self.assertEqual(invalid.returncode, 2, invalid.stderr)

    def test_changed_pdf_cannot_receive_a_response_for_original_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / self.path.name
            changed.write_bytes(self.path.read_bytes() + b'\nchanged')
            document = replace(self.result.document, source_path=changed)
            with self.assertRaises(ValueError):
                apply_corrections(self.result.extraction_run, document, self.response())

    def test_failed_correction_is_not_scored_as_an_unassisted_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            source = write_run(self.result.extraction_run, self.result.document, directory)
            response = directory / 'response.json'
            response.write_text('{}', encoding='utf-8')
            output = directory / 'invalid.html'
            completed = subprocess.run([
                sys.executable, '-m', 'procurement.review', str(self.path), '--source-run', str(source),
                '--review-response', str(response), '--output', str(output)], capture_output=True, text=True)
            self.assertEqual(completed.returncode, 1, completed.stderr)
            self.assertNotIn('Development samples', completed.stdout)
            self.assertNotIn('Sample verdict matches', output.read_text(encoding='utf-8'))

    def test_field_correction_clears_only_its_own_errors(self):
        original = replace(self.result.extraction_run,
                           issues=('line_amount: previous invalid evidence', 'payment_days: invalid evidence',
                                   'Unsupported extra item.'))
        assisted = apply_corrections(original, self.result.document, self.response())
        self.assertNotIn('line_amount: previous invalid evidence', assisted.issues)
        self.assertIn('payment_days: invalid evidence', assisted.issues)
        self.assertIn('Unsupported extra item.', assisted.issues)

    def test_correction_replaces_the_fact_instead_of_only_recording_audit(self):
        original = self.result.extraction_run
        unreadable = replace(original.fields['line_amount'], value=None, status='unrecognized')
        source = replace(original, fields={**original.fields, 'line_amount': unreadable})
        assisted = apply_corrections(source, self.result.document, self.response())
        self.assertEqual(source.fields['line_amount'].status, 'unrecognized')
        self.assertEqual(assisted.fields['line_amount'].status, 'found')
        self.assertEqual(assisted.fields['line_amount'].value, '322,000.00')

    def test_invalid_numeric_and_range_corrections_are_rejected(self):
        for update in ({'value': '-5'}, {'evidence': []}, {'status': 'approved'},
                       {'minimum_value': '999999', 'maximum_value': '1'}):
            response = self.response()
            response['corrections']['line_amount'].update(update)
            with self.subTest(update=update), self.assertRaises(ValueError):
                apply_corrections(self.result.extraction_run, self.result.document, response)
