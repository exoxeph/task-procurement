"""Collect the baseline's supplier, financial and contract facts."""

from procurement.approach1.financial_details import extract_financial_details
from procurement.approach1.supplier_details import extract_supplier_details
from procurement.approach1.terms import extract_terms
from procurement.shared.extraction import ExtractedField
from procurement.shared.pdf_text import PdfDocument


def extract_document(document: PdfDocument) -> dict[str, ExtractedField]:
    """Run the three existing extractors and return their facts together."""
    fields = {}
    fields.update(extract_supplier_details(document))
    fields.update(extract_financial_details(document))
    fields.update(extract_terms(document))
    return fields
