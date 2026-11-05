"""Independent source geometry must overrule an incorrect model item count."""

from dataclasses import asdict, replace
import json
import unittest

from procurement.approach1.extractor import extract_document
from procurement.approach2.schema import parse_response
from procurement.shared.pdf_text import read_pdf
from procurement.shared.references import SAMPLE_DIRECTORY, load_company_rules, load_purchase_request
from procurement.shared.rules import check_rules
from procurement.shared.table_layout import PdfTable


class InputGuardTests(unittest.TestCase):
    def setUp(self):
        source = read_pdf(SAMPLE_DIRECTORY / 'supplier-pack-01.pdf')
        page = replace(source.pages[0], text=source.pages[0].text.replace(
            'after delivery and\nacceptance of goods.', 'after delivery.'))
        self.document = replace(source, pages=(page,))
        self.run = extract_document(self.document)

    def parse_and_review(self, document):
        payload = {'fields': {name: asdict(fact) for name, fact in self.run.fields.items()},
                   'issues': [], 'item_count': 1}
        run = parse_response(json.dumps(payload), document)
        result = check_rules(replace(document, issues=run.issues), run.fields,
                             load_purchase_request(), load_company_rules())
        return run, result

    def test_two_source_rows_cannot_approve_when_model_claims_one(self):
        page = self.document.pages[0]
        table = page.tables[0]
        table = replace(table, rows=table.rows + table.rows)
        run, result = self.parse_and_review(replace(self.document, pages=(replace(page, tables=(table,)),)))
        self.assertNotEqual(result.verdict, 'Approve')
        self.assertTrue(any('item' in issue for issue in run.issues))
        self.assertEqual(run.fields['item_code'].status, 'unrecognized')

    def test_separate_item_tables_across_pages_are_not_one_item(self):
        page = self.document.pages[0]
        extra = replace(page, page_number=2)
        run, result = self.parse_and_review(replace(self.document, pages=(page, extra)))
        self.assertNotEqual(result.verdict, 'Approve')
        self.assertIsNone(run.fields['quantity'].value)

    def test_unrelated_table_does_not_count_as_an_item(self):
        page = self.document.pages[0]
        unrelated = PdfTable(('Contact', 'Value'), (('Office', 'Dhaka'), ('Email', 'example')), (0, 0, 20, 20))
        run, result = self.parse_and_review(replace(self.document, pages=(replace(
            page, tables=page.tables + (unrelated,)),)))
        self.assertEqual(result.verdict, 'Approve')
        self.assertFalse(run.issues)
