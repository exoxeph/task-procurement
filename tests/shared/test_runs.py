"""Saved extractions must retain identity and must never overwrite an old run."""

import json
from pathlib import Path
import tempfile
import unittest

from procurement.shared.extraction import ExtractionRun
from procurement.shared.pdf_text import PdfDocument, PdfPage
from procurement.shared.runs import stamp_run, write_run


class RunTests(unittest.TestCase):
    def test_run_identity_hash_and_raw_response_are_saved_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'fixture.pdf'
            source.write_bytes(b'original document bytes')
            document = PdfDocument(source, (PdfPage(1, 'Original source text'),), ())
            run = stamp_run(ExtractionRun({}, (), {'approach': 'approach2'}, '{"original": true}'), document)
            path = write_run(run, document, Path(directory) / 'runs')
            saved = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(len(saved['metadata']['document_sha256']), 64)
            self.assertEqual(saved['metadata']['run_id'], run.metadata['run_id'])
            self.assertEqual(saved['raw_response'], '{"original": true}')
            self.assertEqual(saved['document']['pages'][0]['text'], 'Original source text')
            with self.assertRaises(FileExistsError):
                write_run(run, document, path.parent)

    def test_changed_document_hash_does_not_reuse_old_run_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.pdf'
            path.write_bytes(b'first')
            document = PdfDocument(path, (), ())
            first = stamp_run(ExtractionRun({}, (), {}), document)
            path.write_bytes(b'second')
            second = stamp_run(ExtractionRun({}, (), {}), document)
            self.assertNotEqual(first.metadata['document_sha256'], second.metadata['document_sha256'])
            self.assertNotEqual(first.metadata['run_id'], second.metadata['run_id'])
