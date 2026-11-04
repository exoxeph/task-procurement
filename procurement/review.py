"""The fixed workflow: read PDF -> extract facts -> check rules -> report."""

from procurement.financial_details import extract_financial_details
from procurement.pdf_text import read_pdf
from procurement.rules import check_rules
from procurement.supplier_details import extract_supplier_details
from procurement.terms import extract_terms


def review_document(path, items, policy):
    document = read_pdf(path)
    fields = {}
    fields.update(extract_supplier_details(document))
    fields.update(extract_financial_details(document))
    fields.update(extract_terms(document))
    return check_rules(document, fields, items, policy)
