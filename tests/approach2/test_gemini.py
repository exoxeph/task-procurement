"""Gemini routing for approach 2, with a fake HTTP boundary: no key or network needed."""

from copy import deepcopy
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from procurement.approach2.gemini import build_gemini_request, extract_document
from procurement.shared.env import load_env
from procurement.shared.extraction import FACT_NAMES
from procurement.shared.pdf_text import PdfDocument, PdfPage

KEY = 'test-key-123'


def answer_json():
    empty = {'value': None, 'status': 'not_found', 'raw_value': None, 'reference_event': None,
             'conditions': [], 'minimum_value': None, 'maximum_value': None, 'evidence': []}
    return json.dumps({'fields': {name: deepcopy(empty) for name in FACT_NAMES}, 'issues': [], 'item_count': 1})


def reply(text=None, finish='STOP', **extra):
    body = {'candidates': [{'content': {'parts': [{'text': text if text is not None else answer_json()}]},
                            'finishReason': finish}],
            'usageMetadata': {'promptTokenCount': 10, 'candidatesTokenCount': 20}, **extra}

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, limit=-1): return json.dumps(body).encode()
    return Response()


class GeminiTests(unittest.TestCase):
    def setUp(self):
        self.document = PdfDocument(Path('fixture.pdf'), (PdfPage(1, 'Quantity 5'),), ())

    def run_with(self, response, key=KEY):
        env = {'GEMINI_API_KEY': key} if key else {}
        with patch.dict(os.environ, env, clear=True), patch('procurement.approach2.gemini.urlopen') as opener:
            if isinstance(response, Exception):
                opener.side_effect = response
            else:
                opener.return_value = response
            return extract_document(self.document), opener

    def test_valid_answer_uses_the_same_validation_and_never_stores_the_key(self):
        run, opener = self.run_with(reply())
        self.assertEqual(run.metadata['status'], 'completed')
        self.assertEqual(run.metadata['provider'], 'gemini')
        self.assertEqual(run.metadata['approach'], 'approach2')
        request = opener.call_args.args[0]
        self.assertEqual(request.get_header('X-goog-api-key'), KEY)
        self.assertNotIn(KEY, request.full_url)
        self.assertNotIn(KEY, json.dumps(run.metadata))

    def test_request_carries_approach2_prompt_and_schema(self):
        body = build_gemini_request(self.document, 'gemini-x')
        self.assertIn('responseJsonSchema', body['generationConfig'])
        self.assertIn('You extract facts', body['systemInstruction']['parts'][0]['text'])
        self.assertEqual(body['generationConfig']['temperature'], 0)

    def test_missing_key_is_a_visible_failed_run_not_a_crash(self):
        run, opener = self.run_with(reply(), key=None)
        self.assertEqual(run.metadata['status'], 'failed')
        self.assertIn('GEMINI_API_KEY', run.metadata['error'])
        opener.assert_not_called()

    def test_truncated_and_malformed_answers_fail_visibly(self):
        cases = (reply(finish='MAX_TOKENS'), reply(text='not json'), reply(text='{"fields": {}}'))
        for response in cases:
            with self.subTest():
                run, _ = self.run_with(response)
                self.assertEqual(run.metadata['status'], 'failed')
                self.assertTrue(all(f.status == 'unrecognized' for f in run.fields.values()))

    def test_error_text_never_echoes_the_key(self):
        run, _ = self.run_with(OSError(f'connection refused for {KEY}'))
        self.assertEqual(run.metadata['status'], 'failed')
        self.assertNotIn(KEY, json.dumps(run.metadata))
        self.assertNotIn(KEY, ' '.join(run.issues))


class EnvTests(unittest.TestCase):
    def test_env_file_fills_missing_variables_but_shell_wins(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            path.write_text('# comment\nGEMINI_API_KEY="from-file"\nGEMINI_MODEL=m1\nEMPTY=\n', encoding='utf-8')
            with patch.dict(os.environ, {'GEMINI_MODEL': 'from-shell'}, clear=True):
                load_env(path)
                self.assertEqual(os.environ['GEMINI_API_KEY'], 'from-file')
                self.assertEqual(os.environ['GEMINI_MODEL'], 'from-shell')
                self.assertNotIn('EMPTY', os.environ)

    def test_missing_env_file_is_fine(self):
        load_env(Path('does-not-exist.env'))


if __name__ == '__main__':
    unittest.main()
