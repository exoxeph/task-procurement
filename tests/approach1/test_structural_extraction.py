"""Structural transformations, not additional supplier benchmark documents."""

import tempfile
import unittest
from pathlib import Path

import pymupdf

from procurement.approach1.financial_details import extract_financial_details
from procurement.shared.pdf_text import PdfDocument, PdfPage, read_pdf
from procurement.approach1.terms import extract_terms


def make_table(path, headers, rows, reverse_insertions=False):
    widths = {'Description': 180, 'Product': 180, 'Unit price (BDT)': 120, 'Amount (BDT)': 120}
    xs = [30]
    for header in headers:
        xs.append(xs[-1] + widths.get(header,160 if 'price' in header.casefold() or 'amount' in header.casefold() else 80))
    ys = [60 + index * 40 for index in range(len(rows) + 2)]
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=1000, height=500)
        for x in xs:
            page.draw_line((x,ys[0]), (x,ys[-1]))
        for y in ys:
            page.draw_line((xs[0],y), (xs[-1],y))
        cells = [(xs[column]+5,ys[row]+15,value) for row, values in enumerate([headers,*rows]) for column,value in enumerate(values)]
        for x,y,value in reversed(cells) if reverse_insertions else cells:
            page.insert_text((x,y),value,fontsize=9)
        pdf.save(path)


class StructuralExtractionTests(unittest.TestCase):
    def extract(self, headers, rows, reverse=False):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'unrelated-name.pdf'
            make_table(path,headers,rows,reverse)
            document = read_pdf(path)
        fields = extract_financial_details(document)
        for field in fields.values():
            for evidence in field.evidence:
                self.assertIn(evidence.text,document.pages[0].text)
        return fields

    def test_reordered_columns_and_pdf_insertion_order_preserve_meaning(self):
        headers = ['Amount (BDT)','Qty','Description','Item','Unit price (BDT)','Unit']
        row = ['123.00','3','Sample material','Z9','41.00','box']
        for reverse in (False,True):
            fields = self.extract(headers,[row],reverse)
            for name,value in zip(('line_amount','quantity','description','item_code','unit_price','unit'),row):
                self.assertEqual(fields[name].value,value,name)

    def test_aliases_wrapping_extra_column_and_number_mutation(self):
        headers = ['SKU','Product','Quantity','UOM','Unit price (BDT)','Amount (BDT)','Note']
        for quantity in ('3','99'):
            fields = self.extract(headers,[['Z9','Sample\nmaterial',quantity,'box','41.00','123.00','blue']])
            self.assertEqual(fields['description'].value,'Sample\nmaterial')
            self.assertEqual(fields['quantity'].value,quantity)

    def test_multiple_rows_duplicate_columns_and_unknown_currency_are_unresolved(self):
        headers = ['Item','Description','Qty','Unit','Unit price (BDT)','Amount (BDT)']
        row = ['Z9','Sample material','3','box','41.00','123.00']
        for hs,rows in [(headers,[row,row]),(headers+['Qty'],[row+['4']]),
                        ([h.replace('BDT','USD') for h in headers],[row]),
                        ([h.replace('BDT','BDT per kg') for h in headers],[row])]:
            self.assertNotEqual(self.extract(hs,rows)['unit_price'].status,'found')

    def test_plain_text_order_is_not_a_table(self):
        document = PdfDocument(Path('fixture.pdf'),(PdfPage(1,'Item\nDescription\nQty\nUnit\nUnit price (BDT)\nAmount (BDT)\nZ9\nSample\n3\nbox\n41.00\n123.00\n'),),())
        field=extract_financial_details(document)['quantity']
        self.assertEqual(field.status,'unrecognized')
        self.assertIsNone(field.value)

    def test_duration_components_allow_concept_order_and_unit_changes(self):
        for text,days in [('Delivery: Within 3 weeks after purchase order.','21'),
                          ('Shipping: After PO, goods arrive within 21 days.','21'),
                          ('Delivery terms: Goods shall be delivered within 21 days of PO.','21')]:
            document=PdfDocument(Path('fixture.pdf'),(PdfPage(1,text),),())
            self.assertEqual(extract_terms(document)['delivery_days'].value,days)

    def test_unexplained_words_and_unknown_anchors_stay_unresolved(self):
        for text in ('Delivery: Within 21 days after invoice.', 'Delivery: Within 21 days after PO, provided stock exists.',
                     'Delivery: Within 21 days after PO or 40 days after payment.', 'Delivery: No delivery within 21 days after PO.',
                     'Delivery: Within 21 days after PO যদি মজুদ থাকে.',
                     'Delivery: Within 21 days after PO 仅限现货.'):
            document=PdfDocument(Path('fixture.pdf'),(PdfPage(1,text),),())
            self.assertNotEqual(extract_terms(document)['delivery_days'].status,'found')

    def test_raw_clauses_and_reference_components_remain_visible(self):
        text='Payment terms: Balance within 60 days after delivery.\nQuotation validity: Valid for 4 weeks from quotation date.'
        fields=extract_terms(PdfDocument(Path('fixture.pdf'),(PdfPage(1,text),),()))
        self.assertEqual(fields['payment_days'].value,'60')
        self.assertEqual(fields['payment_reference'].value,'delivery')
        self.assertEqual(fields['validity_days'].value,'28')
        self.assertEqual(fields['validity_reference'].value,'quotation_date')
        self.assertIn(fields['payment_clause_text'].value,text)

    def test_second_borderless_or_incomplete_grid_is_not_silently_ignored(self):
        headers=['Item','Description','Qty','Unit','Unit price (BDT)','Amount (BDT)']
        row=['Z9','Sample material','3','box','41.00','123.00']
        for incomplete in (False,True):
            with tempfile.TemporaryDirectory() as folder:
                first=Path(folder)/'first.pdf'
                output=Path(folder)/'two-tables.pdf'
                make_table(first,headers,[row])
                with pymupdf.open(first) as pdf:
                    page=pdf.new_page(width=900,height=500)
                    if incomplete:
                        page.draw_rect((30,60,850,140))
                        page.draw_line((30,100),(850,100))
                    for index,(header,value) in enumerate(zip(headers,row)):
                        page.insert_text((35+index*130,80),header,fontsize=8)
                        page.insert_text((35+index*130,120),value,fontsize=8)
                    pdf.save(output)
                document=read_pdf(output)
            self.assertNotEqual(extract_financial_details(document)['unit_price'].status,'found')


if __name__ == '__main__':
    unittest.main()
