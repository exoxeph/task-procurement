"""Policy boundary tests run through real extraction and the actual rule engine."""

import unittest
from pathlib import Path

from procurement.financial_details import extract_financial_details
from procurement.pdf_text import PdfDocument, PdfPage, read_pdf
from procurement.references import load_company_rules, load_purchase_request
from procurement.rules import check_rules
from procurement.supplier_details import extract_supplier_details
from procurement.terms import extract_terms

SAMPLES = Path(__file__).resolve().parents[1] / 'sample-data/engineer/task1-procurement'


class RuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = load_purchase_request()
        cls.policy = load_company_rules()
        cls.clean = read_pdf(SAMPLES / 'supplier-pack-01.pdf')

    def review(self, replacements=(), document=None):
        if document is None:
            text = self.clean.pages[0].text
            for old, new in replacements:
                self.assertIn(old, text)
                text = text.replace(old, new)
            document = PdfDocument(Path('fixture.pdf'), (PdfPage(1, text),), ())
        fields = {**extract_supplier_details(document), **extract_financial_details(document), **extract_terms(document)}
        return check_rules(document, fields, self.items, self.policy)

    def codes(self, result):
        return {finding.code for finding in result.findings}

    def test_all_ten_verdicts(self):
        expected = ['Approve','Approve','Reject','Needs a person to check','Reject',
                    'Reject','Needs a person to check','Reject','Needs a person to check','Reject']
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
                         ('after delivery and\nacceptance of goods.', 'after delivery or immediately on demand.')]:
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
        document = PdfDocument(Path('fixture.pdf'), (PdfPage(1,included),PdfPage(2,excluded)), ())
        result = self.review(document=document)
        self.assertEqual(result.fields['unit_price_tax_note'].status, 'ambiguous')
        self.assertEqual(result.verdict, 'Needs a person to check')

    def test_oversized_amount_requires_review_without_crashing(self):
        result = self.review([('5,664,000.00', '999999999999999999999999999999999999999.00')])
        self.assertEqual(result.verdict, 'Needs a person to check')


if __name__ == '__main__':
    unittest.main()
