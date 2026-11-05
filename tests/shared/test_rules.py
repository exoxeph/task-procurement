"""Policy boundary tests run through real extraction and the actual rule engine."""

import unittest
from pathlib import Path
from dataclasses import replace

from procurement.shared.pdf_text import PdfDocument, PdfPage, read_pdf
from procurement.shared.references import load_company_rules, load_purchase_request
from procurement.shared.rules import check_rules
from procurement.approach1.extractor import extract_document
from procurement.shared.extraction import Evidence, ExtractedField

SAMPLES = Path(__file__).resolve().parents[2] / 'sample-data/engineer/task1-procurement'


class RuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = load_purchase_request()
        cls.policy = load_company_rules()
        source = read_pdf(SAMPLES / 'supplier-pack-01.pdf')
        # A controlled unqualified payment statement isolates policy boundaries.
        # The original sample's acceptance wording is now intentionally unresolved.
        page = replace(source.pages[0], text=source.pages[0].text.replace('after delivery and\nacceptance of goods.', 'after delivery.'))
        cls.clean = replace(source, pages=(page,))

    def review(self, replacements=(), document=None):
        if document is None:
            page = self.clean.pages[0]
            text = page.text
            tables = page.tables
            outside = page.outside_tables_text
            for old, new in replacements:
                self.assertIn(old, text)
                text = text.replace(old, new)
                def change_cell(cell):
                    return new.strip() if old.startswith('\n') and cell == old.strip() else cell.replace(old,new)
                tables = tuple(replace(table,headers=tuple(change_cell(cell) for cell in table.headers),
                                       rows=tuple(tuple(change_cell(cell) for cell in row) for row in table.rows)) for table in tables)
                outside = outside.replace(old,new) if outside is not None else None
            document = PdfDocument(Path('fixture.pdf'), (replace(page,text=text,tables=tables,outside_tables_text=outside),), ())
        fields = extract_document(document).fields
        return check_rules(document, fields, self.items, self.policy)

    def codes(self, result):
        return {finding.code for finding in result.findings}

    def test_all_ten_actual_verdicts_include_conservative_escalations(self):
        expected = ['Needs a person to check','Needs a person to check','Reject','Needs a person to check','Reject',
                    'Needs a person to check','Needs a person to check','Needs a person to check','Needs a person to check','Reject']
        for number, verdict in enumerate(expected, 1):
            with self.subTest(pack=number):
                result = self.review(document=read_pdf(SAMPLES / f'supplier-pack-{number:02}.pdf'))
                self.assertEqual(result.verdict, verdict, result.findings)
                for finding in result.findings:
                    self.assertTrue(finding.evidence)

    def test_price_boundary_uses_exact_decimal_math(self):
        # A's maximum is 480; exactly 3% above is 494.40.
        for price, code, severity in [('480.00',None,None), ('480.01','price','Needs a person to check'),
                                      ('494.40','price','Needs a person to check'), ('494.41','price','Reject')]:
            result = self.review([('472.00',price)])
            price_findings = [finding for finding in result.findings if finding.code == 'price']
            self.assertEqual(len(price_findings), int(code is not None))
            if price_findings:
                self.assertEqual(price_findings[0].severity, severity)

    def test_quantity_exactly_five_percent_is_allowed(self):
        self.assertNotIn('quantity', self.codes(self.review([('12,000','12,600')])))
        self.assertIn('quantity', self.codes(self.review([('12,000','12,601')])))

    def test_advance_boundary(self):
        self.assertNotIn('advance', self.codes(self.review([('10% advance','20% advance')])))
        result = self.review([('10% advance','20.01% advance')])
        self.assertEqual(result.verdict, 'Reject')
        self.assertIn('advance', self.codes(result))

    def test_delivery_boundaries(self):
        for days, expected in [(30,'Approve'),(31,'Needs a person to check'),(45,'Needs a person to check'),(46,'Reject')]:
            self.assertEqual(self.review([('within 24 days',f'within {days} days')]).verdict, expected)

    def test_payment_and_validity_boundaries(self):
        for days, expected in [(29,True),(30,False),(60,False),(61,True)]:
            self.assertEqual('payment' in self.codes(self.review([('within 45 days after',f'within {days} days after')])), expected)
        self.assertIn('validity', self.codes(self.review([('valid for 45 days','valid for 29 days')])))
        self.assertNotIn('validity', self.codes(self.review([('valid for 45 days','valid for 30 days')])))

    def test_penalty_missing_explicitly_absent_weak_or_unclear(self):
        self.assertIn('penalty_missing', self.codes(self.review([('Late delivery penalty: 1% of order value for each full week of delay.', 'No late delivery penalty applies.')])))
        weak = self.review([('penalty: 1%', 'penalty: 0.49%')])
        self.assertIn('penalty_rate', self.codes(weak))
        self.assertEqual(weak.verdict, 'Needs a person to check')
        self.assertNotIn('penalty_rate', self.codes(self.review([('penalty: 1%', 'penalty: 0.5%')])) )

    def test_unknown_registration_is_review_not_automatic_reject(self):
        result = self.review([('Supplier TIN: 101458013391 BIN: 000170141-0101','Unrecognized registration layout')])
        self.assertEqual(result.verdict, 'Needs a person to check')
        self.assertNotIn('registration_missing', self.codes(result))

    def test_arithmetic_checks_all_stated_figures(self):
        for old, new, code in [('5,664,000.00','5,664,001.00','line_arithmetic'),
                               ('849,600.00','849,601.00','vat_arithmetic'),
                               ('6,513,600.00','6,513,601.00','total_arithmetic')]:
            self.assertIn(code, self.codes(self.review([(old,new)])))

    def test_bad_request_item_or_unit_never_approves(self):
        for old, new in [('PR-2026-114','PR-2026-999'), ('\nA\n','\nUNKNOWN\n'), ('\nmetre\n','\npiece\n')]:
            self.assertEqual(self.review([(old,new)]).verdict, 'Needs a person to check')

    def test_pdf_issue_and_conflicting_values_never_approve(self):
        issue = PdfDocument(self.clean.source_path, self.clean.pages, ('Blank page',))
        self.assertEqual(self.review(document=issue).verdict, 'Needs a person to check')
        conflict = PdfDocument(self.clean.source_path, self.clean.pages + (PdfPage(2, 'Total: 1.00\n'),), ())
        self.assertEqual(self.review(document=conflict).verdict, 'Needs a person to check')

    def test_reject_keeps_review_findings(self):
        result = self.review([('10% advance','40% advance'), ('within 45 days after','within 90 days after')])
        self.assertEqual(result.verdict, 'Reject')
        self.assertTrue({'advance','payment'}.issubset(self.codes(result)))

    def test_qualified_delivery_or_payment_does_not_approve(self):
        for old, new in [('the purchase order.\n3. Delay', 'the purchase order provided stock is available.\n3. Delay'),
                         ('after delivery.', 'after delivery or immediately on demand.')]:
            self.assertEqual(self.review([(old,new)]).verdict, 'Needs a person to check')

    def test_contradictory_advance_does_not_approve(self):
        result = self.review([('10% advance','No advance payment required. 40% advance')])
        self.assertEqual(result.fields['advance_percent'].status, 'ambiguous')
        self.assertEqual(result.verdict, 'Needs a person to check')

    def test_signed_or_malformed_percentages_are_not_accepted_as_positive_suffixes(self):
        for value in ('-0.5', '+0.5', '1,0.5', '.0.5'):
            for old, new in [('penalty: 1%', f'penalty: {value}%'), ('10% advance',f'{value}% advance')]:
                with self.subTest(value=value, field=old):
                    self.assertEqual(self.review([(old,new)]).verdict, 'Needs a person to check')

    def test_conflicting_tax_notes_require_review(self):
        text = self.clean.pages[0].text
        included = text.replace('Unit price (BDT)', 'Unit price (BDT, VAT included)')
        excluded = text.replace('Unit price (BDT)', 'Unit price (BDT, VAT excluded)')
        page = self.clean.pages[0]
        def tax_page(number,text,note):
            tables=tuple(replace(table,headers=tuple(h.replace('Unit price (BDT)',f'Unit price (BDT, VAT {note})') for h in table.headers)) for table in page.tables)
            return replace(page,page_number=number,text=text,tables=tables)
        document = PdfDocument(Path('fixture.pdf'), (tax_page(1,included,'included'),tax_page(2,excluded,'excluded')), ())
        result = self.review(document=document)
        self.assertEqual(result.fields['unit_price_tax_note'].status, 'ambiguous')
        self.assertEqual(result.verdict, 'Needs a person to check')

    def test_oversized_amount_requires_review_without_crashing(self):
        result = self.review([('5,664,000.00', '999999999999999999999999999999999999999.00')])
        self.assertEqual(result.verdict, 'Needs a person to check')

    def test_missing_penalty_and_registration_do_not_use_template_absence_heuristics(self):
        for pack in (6,8):
            result=self.review(document=read_pdf(SAMPLES / f'supplier-pack-{pack:02}.pdf'))
            self.assertEqual(result.verdict,'Needs a person to check')
            self.assertNotIn('penalty_missing',self.codes(result))
            self.assertNotIn('registration_missing',self.codes(result))

    def test_explicit_labelled_missing_registration_still_rejects(self):
        result=self.review([('TIN: 101458013391','TIN: not provided;')])
        self.assertEqual(result.verdict,'Reject')
        self.assertIn('registration_missing',self.codes(result))

    def test_every_percentage_must_be_interpreted_and_consistent(self):
        for old,new in [('10% advance','10% advance 40%'),('Balance payable','Balance 190% payable'),
                        ('Balance payable','Balance 10% payable')]:
            with self.subTest(text=new):
                self.assertEqual(self.review([(old,new)]).verdict,'Needs a person to check')

    def test_one_obligation_cannot_supply_another_obligations_deadline(self):
        result=self.review([('Delivery within 24 days of receiving the purchase order.',
                             'Payment within 24 days of receiving the purchase order.')])
        self.assertEqual(result.verdict,'Needs a person to check')

    def test_unreadable_extra_item_table_does_not_hide_behind_supported_table(self):
        page=PdfPage(2,'Item\nDescription\nQty\nUnit\nUnit price (BDT)\nAmount (BDT)\nB\nPolyester\n100\npiece\n50\n5000\n')
        result=self.review(document=replace(self.clean,pages=self.clean.pages+(page,)))
        self.assertEqual(result.verdict,'Needs a person to check')

    def test_foreign_currency_summary_cannot_be_used_as_bdt(self):
        self.assertEqual(self.review([('Total','Total (USD)')]).verdict,'Needs a person to check')

    def test_duration_reference_conditions_and_ranges_cannot_silently_pass(self):
        original = self.review().fields
        for name, changes in (
            ('payment_days', {'reference_event': 'invoice'}),
            ('delivery_days', {'reference_event': 'delivery'}),
            ('validity_days', {'reference_event': 'purchase_order'}),
            ('payment_days', {'reference_event': None}),
            ('payment_days', {'conditions': ('after acceptance',)}),
            ('delivery_days', {'minimum_value': '24', 'maximum_value': '42'}),
        ):
            with self.subTest(name=name, changes=changes):
                fields = {**original, name: replace(original[name], **changes)}
                if 'reference_event' in changes:
                    reference_name = name.removesuffix('_days') + '_reference'
                    event = changes['reference_event']
                    fields[reference_name] = replace(fields[reference_name], value=event,
                                                     status='found' if event else 'not_found')
                result = check_rules(self.clean, fields, self.items, self.policy)
                self.assertEqual(result.verdict, 'Needs a person to check')
                self.assertNotIn('extraction_issue', self.codes(result))

    def test_wrong_reference_cannot_produce_a_false_delivery_rejection(self):
        fields = self.review().fields.copy()
        fields['delivery_days'] = replace(fields['delivery_days'], value='60', reference_event='invoice',
                                          minimum_value='60', maximum_value='60')
        fields['delivery_reference'] = replace(fields['delivery_reference'], value='invoice')
        result = check_rules(self.clean, fields, self.items, self.policy)
        self.assertEqual(result.verdict, 'Needs a person to check')
        fields['advance_percent'] = replace(fields['advance_percent'], value='40',
                                            minimum_value='40', maximum_value='40')
        self.assertEqual(check_rules(self.clean, fields, self.items, self.policy).verdict, 'Reject')

    def test_unsupported_currency_does_not_trigger_bdt_price_rejection(self):
        for currency in ('USD', None):
            fields = self.review().fields.copy()
            fields['currency'] = ExtractedField(currency, 'found' if currency else 'not_found',
                                                (Evidence(1, self.clean.pages[0].text),) if currency else ())
            fields['unit_price'] = replace(fields['unit_price'], value='999',
                                           minimum_value='999', maximum_value='999')
            result = check_rules(self.clean, fields, self.items, self.policy)
            self.assertEqual(result.verdict, 'Needs a person to check')
            self.assertNotIn('price', self.codes(result))
            self.assertIn('currency', self.codes(result))

    def test_supported_excerpt_alone_cannot_establish_penalty_absence(self):
        fields = self.review().fields.copy()
        fields['penalty_clause'] = replace(fields['penalty_clause'], value='absent')
        result = check_rules(self.clean, fields, self.items, self.policy)
        self.assertEqual(result.verdict, 'Needs a person to check')
        self.assertNotIn('penalty_missing', self.codes(result))

    def test_a_conditional_penalty_absence_is_review_not_a_definite_rejection(self):
        original = self.review([('Late delivery penalty: 1% of order value for each full week of delay.',
                                'No late delivery penalty applies.')])
        fields = original.fields.copy()
        fields['penalty_clause'] = replace(fields['penalty_clause'], conditions=('only during a strike',))
        result = check_rules(original.document, fields, self.items, self.policy)
        self.assertEqual(result.verdict, 'Needs a person to check')

    def test_ambiguous_raw_clause_cannot_be_hidden_by_a_simple_duration(self):
        fields = self.review().fields.copy()
        fields['payment_clause_text'] = replace(fields['payment_clause_text'], status='ambiguous', value=None)
        self.assertEqual(check_rules(self.clean, fields, self.items, self.policy).verdict, 'Needs a person to check')


if __name__ == '__main__':
    unittest.main()
