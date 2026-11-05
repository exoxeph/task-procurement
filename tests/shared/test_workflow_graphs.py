"""The fixed LangGraph workflow: straight lines, who does each step, progress events, fail-closed."""

import contextlib
from dataclasses import replace
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from procurement.approach1.extractor import extract_document as baseline_extract
from procurement.review import review_document
from procurement.shared.extraction import ExtractedField, ExtractionRun, FACT_NAMES
from procurement.shared.pdf_text import read_pdf
from procurement.shared.references import SAMPLE_DIRECTORY, load_company_rules, load_purchase_request
from procurement.shared.rules import ReviewResult
from procurement.workflow import APPROACHES, build_graph, describe, main, mermaid, run_workflow

PDF = SAMPLE_DIRECTORY / 'supplier-pack-05.pdf'
EXPECTED_NODES = {
    'approach1': ['read_pdf', 'extract_python', 'validate', 'decide_rules', 'persist', 'report'],
    'approach2': ['read_pdf', 'extract_ai', 'validate', 'decide_rules', 'persist', 'report'],
    'approach3': ['read_pdf', 'extract_ai_typed', 'validate', 'decide_rules', 'persist', 'report'],
    'approach4': ['read_pdf', 'agent1_extract', 'annotate_warnings', 'agent2_judge', 'persist', 'report'],
}


class GraphShapeTests(unittest.TestCase):
    def test_each_approach_is_a_straight_line_in_the_expected_order(self):
        for approach, expected in EXPECTED_NODES.items():
            with self.subTest(approach=approach):
                graph = build_graph(approach).get_graph()
                self.assertEqual([n for n in graph.nodes if not n.startswith('__')], expected)
                edges = [(e.source, e.target) for e in graph.edges]  # the library gives no edge order
                self.assertEqual(sorted(edges), sorted(zip(['__start__'] + expected, expected + ['__end__'])))

    def test_no_graph_has_a_branch_or_a_loop(self):
        for approach in APPROACHES:
            for corrected in (False, True):
                with self.subTest(approach=approach, corrected=corrected):
                    edges = build_graph(approach, corrected).get_graph().edges
                    self.assertFalse(any(e.conditional for e in edges))
                    sources = [e.source for e in edges]
                    self.assertEqual(len(sources), len(set(sources)), 'every step has exactly one next step')

    def test_only_the_model_steps_are_marked_ai(self):
        actors = {approach: [s['node'] for s in describe(approach) if s['actor'] == 'ai'] for approach in APPROACHES}
        self.assertEqual(actors, {'approach1': [], 'approach2': ['extract_ai'], 'approach3': ['extract_ai_typed'],
                                  'approach4': ['agent1_extract', 'agent2_judge']})

    def test_a_correction_run_swaps_the_model_call_for_the_recorded_correction(self):
        nodes = [s['node'] for s in describe('approach3', corrected=True)]
        self.assertEqual(nodes[1], 'apply_human_correction')
        self.assertNotIn('extract_ai_typed', nodes)

    def test_unknown_approach_is_refused(self):
        with self.assertRaisesRegex(ValueError, 'Unknown extraction approach'):
            build_graph('approach9')

    def test_mermaid_is_generated_from_the_real_nodes_and_written_per_approach(self):
        text = mermaid('approach4')
        for node in EXPECTED_NODES['approach4']:
            self.assertIn(node, text)
        with tempfile.TemporaryDirectory() as directory, patch('sys.argv', ['workflow', '--write', directory]), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(), 0)
            self.assertEqual(sorted(p.name for p in Path(directory).iterdir()),
                             [f'{a}.mmd' for a in APPROACHES])


class RunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items, cls.policy = load_purchase_request(), load_company_rules()

    def test_baseline_run_emits_one_event_per_step_in_order_and_matches_review_document(self):
        events = []
        result = run_workflow(PDF, self.items, self.policy, approach='approach1', on_step=events.append)
        self.assertEqual([e['node'] for e in events], EXPECTED_NODES['approach1'])
        self.assertEqual([e['actor'] for e in events], ['code'] * 6)
        self.assertTrue(all(e['seconds'] >= 0 and e['label'] for e in events))
        same = review_document(PDF, self.items, self.policy, approach='approach1')
        self.assertEqual((result.verdict, [f.code for f in result.findings]),
                         (same.verdict, [f.code for f in same.findings]))
        self.assertEqual([s['name'] for s in result.steps][0], 'Read PDF')

    def test_half_a_correction_request_fails_after_reading_the_pdf(self):
        with self.assertRaisesRegex(ValueError, 'requires both'):
            review_document(PDF, self.items, self.policy, source_run=Path('x.json'))

    def fake_agent1(self, status='completed'):
        metadata = {'approach': 'approach4', 'status': status, 'model': 'm',
                    'warnings': {}, 'notes': {}, 'elapsed_seconds': 1.0}
        if status == 'failed':
            # A real failed run: nothing was read, so every fact is unrecognized.
            fields = {name: ExtractedField(None, 'unrecognized', ()) for name in FACT_NAMES}
            return ExtractionRun(fields, ('Extraction failed: timed out',), metadata)
        return replace(baseline_extract(read_pdf(PDF)), metadata=metadata)

    def test_approach4_runs_reader_then_annotation_then_judge_in_a_fixed_order(self):
        def fake_judge(checked, run, items, policy, **options):
            return (ReviewResult(checked, run.fields, (), 'Approve'),
                    {'status': 'completed', 'elapsed_seconds': 0.5, 'model': 'j'})

        events = []
        with patch('procurement.approach4.extractor.extract_document', return_value=self.fake_agent1()), \
                patch('procurement.approach4.judge.judge', side_effect=fake_judge) as judge:
            result = run_workflow(PDF, self.items, self.policy, approach='approach4', provider='openrouter',
                                  on_step=events.append)
        self.assertEqual([e['node'] for e in events], EXPECTED_NODES['approach4'])
        self.assertEqual([e['actor'] for e in events], ['code', 'ai', 'code', 'ai', 'code', 'code'])
        judge.assert_called_once()
        self.assertEqual(result.verdict, 'Approve')
        self.assertEqual(result.extraction_run.metadata['judge']['model'], 'j')
        self.assertEqual(result.extraction_run.metadata['elapsed_seconds'], 1.5)
        self.assertTrue(result.steps[1]['name'].startswith('Agent 1'))

    def test_a_failed_reader_skips_the_judge_and_ends_with_a_person(self):
        with patch('procurement.approach4.extractor.extract_document',
                   return_value=self.fake_agent1(status='failed')), \
                patch('procurement.approach4.judge.judge') as judge:
            result = run_workflow(PDF, self.items, self.policy, approach='approach4', provider='openrouter')
        judge.assert_not_called()
        self.assertEqual(result.verdict, 'Needs a person to check')
        self.assertEqual([f.code for f in result.findings], ['extraction_failed'])

    def test_a_judge_that_fails_is_recorded_and_never_an_approval(self):
        def failing_judge(checked, run, items, policy, **options):
            return (ReviewResult(checked, run.fields, (), 'Needs a person to check'),
                    {'status': 'failed', 'elapsed_seconds': 0.2, 'error': 'timed out'})

        with patch('procurement.approach4.extractor.extract_document', return_value=self.fake_agent1()), \
                patch('procurement.approach4.judge.judge', side_effect=failing_judge):
            result = run_workflow(PDF, self.items, self.policy, approach='approach4', provider='openrouter')
        self.assertEqual(result.extraction_run.metadata['status'], 'failed')
        self.assertEqual(result.verdict, 'Needs a person to check')


if __name__ == '__main__':
    unittest.main()
