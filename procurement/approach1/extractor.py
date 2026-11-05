"""Collect the baseline's supplier, financial and contract facts."""

from procurement.approach1.financial_details import extract_financial_details
from procurement.approach1.supplier_details import extract_supplier_details
from procurement.approach1.terms import extract_terms
from dataclasses import replace
import re

from procurement.shared.extraction import Evidence, ExtractedField, ExtractionRun, NUMERIC_FIELDS, validate_fields
from procurement.shared.pdf_text import PdfDocument


def extract_document(document: PdfDocument) -> ExtractionRun:
    """Run the three existing extractors and return their facts together."""
    fields = {}
    fields.update(extract_supplier_details(document))
    fields.update(extract_financial_details(document))
    fields.update(extract_terms(document))
    # The baseline already extracts these references separately. Preserve them
    # on the duration itself so policy checks cannot confuse starting events.
    for kind in ("payment", "delivery", "validity"):
        reference = fields[kind + "_reference"]
        fields[kind + "_days"] = replace(fields[kind + "_days"],
            reference_event=reference.value if reference.status == "found" else None)

    # Financial extraction accepts only explicit BDT price/amount headings.
    # Do not assume a currency just because the purchase request uses BDT.
    currency_evidence = []
    if all(fields[name].status == "found" for name in ("unit_price", "line_amount")):
        for page in document.pages:
            if any(re.search(r"\bBDT\b|\u09f3", " ".join(table.headers), re.I) for table in page.tables):
                currency_evidence.append(Evidence(page.page_number, page.text))
    fields["currency"] = ExtractedField("BDT", "found", tuple(currency_evidence)) if currency_evidence else ExtractedField(None, "not_found", ())
    for name, fact in fields.items():
        raw = fact.value if fact.value and any(fact.value in excerpt.text for excerpt in fact.evidence) else None
        bounds = fact.value if name in NUMERIC_FIELDS and fact.status == "found" else None
        fields[name] = replace(fact, raw_value=raw, minimum_value=bounds, maximum_value=bounds)
    run = validate_fields(fields, document)
    return replace(run, metadata={"approach": "approach1"})
