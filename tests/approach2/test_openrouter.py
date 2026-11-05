"""OpenRouter routing for approach 2, with a fake HTTP boundary: no key or network needed."""

from copy import deepcopy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from procurement.approach2.openrouter import build_openrouter_request, extract_document
from procurement.shared.extraction import FACT_NAMES
from procurement.shared.pdf_text import PdfDocument, PdfPage

KEY = 'test-key-123'


def answer_json():
    empty = {'value': None, 'status': 'not_found', 'raw_value': None, 'reference_event': None,
             'conditions': [], 'minimum_value': None, 'maximum_value': None, 'evidence': []}
    return json.dumps({'fields': {name: deepcopy(empty) for name in FACT_NAMES}, 'issues': [], 'item_count': 1})


def reply(text=None, finish='stop', **extra):
    body = {'model': 'qwen/qwen3-14b', 'provider': 'FakeHost',
            'choices': [{'message': {'content': text if text is not None else answer_json()},
                         'finish_reason': finish}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 20, 'total_tokens': 30}, **extra}

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, limit=-1): return json.dumps(body).encode()
    return Response()


class OpenRouterTests(unittest.TestCase):
    def setUp(self):
        self.document = PdfDocument(Path('fixture.pdf'), (PdfPage(1, 'Quantity 5'),), ())

    def run_with(self, response, key=KEY):
        env = {'OPENROUTER_API_KEY': key} if key else {}
        with patch.dict(os.environ, env, clear=True), patch('procurement.approach2.openrouter.urlopen') as opener:
            if isinstance(response, Exception):
                opener.side_effect = response
            else:
                opener.return_value = response
            return extract_document(self.document), opener

    def test_valid_answer_is_validated_and_never_stores_the_key(self):
        run, opener = self.run_with(reply())
        self.assertEqual(run.metadata['status'], 'completed')
        self.assertEqual((run.metadata['provider'], run.metadata['approach']), ('openrouter', 'approach2'))
        self.assertEqual(run.metadata['served_by'], 'FakeHost')
        request = opener.call_args.args[0]
        self.assertEqual(request.get_header('Authorization'), 'Bearer ' + KEY)
        self.assertNotIn(KEY, request.full_url)
        self.assertNotIn(KEY, json.dumps(run.metadata))

    def test_request_uses_approach2_prompt_schema_and_requires_schema_support(self):
        body = build_openrouter_request(self.document, 'qwen/qwen3-14b')
        self.assertEqual(body['response_format']['type'], 'json_schema')
        self.assertTrue(body['provider']['require_parameters'])
        self.assertEqual(body['temperature'], 0)
        self.assertIn('You extract facts', body['messages'][0]['content'])

    def test_ignored_backends_are_passed_to_openrouter_only_when_configured(self):
        with patch.dict(os.environ, {'OPENROUTER_IGNORE_PROVIDERS': ' NextBit , Other '}, clear=True):
            self.assertEqual(build_openrouter_request(self.document, 'qwen/qwen3-14b')['provider'],
                             {'require_parameters': True, 'ignore': ['NextBit', 'Other']})
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(build_openrouter_request(self.document, 'qwen/qwen3-14b')['provider'],
                             {'require_parameters': True})

    def test_missing_key_is_a_visible_failed_run_not_a_crash(self):
        run, opener = self.run_with(reply(), key=None)
        self.assertEqual(run.metadata['status'], 'failed')
        self.assertIn('OPENROUTER_API_KEY', run.metadata['error'])
        opener.assert_not_called()

    def test_truncated_malformed_and_error_answers_fail_visibly(self):
        cases = (reply(finish='length'), reply(text='not json'), reply(text='{"fields": {}}'),
                 reply(error={'message': 'no providers'}))
        for response in cases:
            with self.subTest():
                run, _ = self.run_with(response)
                self.assertEqual(run.metadata['status'], 'failed')
                self.assertTrue(all(f.status == 'unrecognized' for f in run.fields.values()))

    def test_error_text_never_echoes_the_key(self):
        run, _ = self.run_with(OSError(f'connection refused for {KEY}'))
        self.assertNotIn(KEY, json.dumps(run.metadata))
        self.assertNotIn(KEY, ' '.join(run.issues))

    def test_bad_model_slug_is_rejected_before_any_request(self):
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': KEY}, clear=True), \
                patch('procurement.approach2.openrouter.urlopen') as opener:
            run = extract_document(self.document, model='bad model; drop')
        self.assertEqual(run.metadata['status'], 'failed')
        opener.assert_not_called()


if __name__ == '__main__':
    unittest.main()
