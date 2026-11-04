"""Terms read from supplied documents, plus small uncertainty regressions."""

import unittest
from pathlib import Path

from procurement.pdf_text import PdfDocument, PdfPage, read_pdf
from procurement.terms import extract_terms

SAMPLES = Path(__file__).resolve().parents[1] / "sample-data/engineer/task1-procurement"


class TermsTests(unittest.TestCase):
    def test_all_ten_terms_and_exact_evidence(self):
        # advance, payment days, delivery days, penalty percent, validity days
        # Uninterpreted source values stay unresolved, even though a person can
        # read them: acceptance wording and factory-location wording are outside
        # the small component grammar. Manual gold verdicts remain unchanged.
        expected = [(10,None,24,"1",45),(0,30,None,"0.75",30),(15,40,20,"0.5",30),
                    (10,30,28,"0.6",40),(40,30,25,"1",30),(10,60,27,None,30),
                    (0,45,22,"0.5",35),(10,30,18,"0.5",30),(5,None,28,"0.5",30),
                    (10,45,60,"0.5",30)]
        for number, values in enumerate(expected, 1):
            document = read_pdf(SAMPLES / f"supplier-pack-{number:02}.pdf")
            fields = extract_terms(document)
            for name, value in zip(("advance_percent","payment_days","delivery_days","penalty_percent","validity_days"), values):
                with self.subTest(pack=number, field=name):
                    self.assertEqual(fields[name].value, str(value) if value is not None else None)
            for field in fields.values():
                for evidence in field.evidence:
                    self.assertIn(evidence.text, document.pages[evidence.page_number - 1].text)
        self.assertEqual(extract_terms(read_pdf(SAMPLES / 'supplier-pack-09.pdf'))['payment_days'].status, 'unrecognized')
        self.assertEqual(extract_terms(read_pdf(SAMPLES / 'supplier-pack-06.pdf'))['penalty_clause'].status, 'not_found')
        self.assertEqual(extract_terms(read_pdf(SAMPLES / 'supplier-pack-08.pdf'))['penalty_basis'].status, 'unrecognized')

    def test_missing_and_conflicting_terms_are_not_guessed(self):
        document = PdfDocument(Path('fixture.pdf'), (PdfPage(1, '1. Delivery. Delivery within 20 days of PO.\n2. Delivery. Delivery within 25 days of PO.\n'),), ())
        fields = extract_terms(document)
        self.assertEqual(fields['delivery_days'].status, 'ambiguous')
        self.assertEqual(fields['payment_days'].status, 'not_found')

    def test_unknown_anchor_conditions_and_negation_require_review(self):
        for text in ('Delivery within 20 days of invoice.', 'Delivery within 20 days of PO if stock is available.',
                     'Delivery not within 20 days of PO.'):
            document = PdfDocument(Path('fixture.pdf'), (PdfPage(1, '1. Delivery. ' + text),), ())
            self.assertEqual(extract_terms(document)['delivery_days'].status, 'unrecognized')

    def test_explicit_no_penalty_is_distinct_from_unknown(self):
        document = PdfDocument(Path('fixture.pdf'), (PdfPage(1, '3. Delay. No late delivery penalty applies.\n'),), ())
        self.assertEqual(extract_terms(document)['penalty_clause'].value, 'absent')


if __name__ == '__main__':
    unittest.main()
