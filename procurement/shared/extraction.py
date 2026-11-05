"""Small records shared by the baseline's document extraction steps."""

from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
import argparse
import json
from pathlib import Path
import re
import sys

from procurement.shared.pdf_text import PdfDocument, PdfReadError, read_pdf
from procurement.shared.table_layout import item_columns


FACT_NAMES = (
    "supplier_name", "quotation_number", "quotation_date", "purchase_request_reference", "tin", "bin",
    "item_code", "description", "quantity", "unit", "unit_price", "line_amount",
    "subtotal", "vat_rate", "vat_amount", "total", "unit_price_tax_note", "currency",
    "advance_percent", "payment_days", "delivery_days", "penalty_clause", "penalty_percent",
    "penalty_basis", "validity_days", "payment_clause_text", "delivery_clause_text",
    "penalty_clause_text", "validity_clause_text", "payment_reference", "delivery_reference", "validity_reference",
)
NUMERIC_FIELDS = (
    "quantity", "unit_price", "line_amount", "subtotal", "vat_rate", "vat_amount", "total",
    "advance_percent", "payment_days", "delivery_days", "penalty_percent", "validity_days",
)
WHOLE_NUMBER_FIELDS = ("quantity", "payment_days", "delivery_days", "validity_days")
STATUSES = ("found", "not_found", "unrecognized", "ambiguous")


@dataclass(frozen=True)
class Evidence:
    """An exact text excerpt and the page it came from."""

    page_number: int
    text: str


@dataclass(frozen=True)
class ExtractedField:
    """A value, its extraction state, and supporting source excerpts.

    found: one distinct recognized value.
    not_found: no recognized label or supplier-name candidate.
    unrecognized: a label exists but its value is missing or unsupported.
    ambiguous: multiple distinct recognized values.
    """

    value: str | None
    status: str
    evidence: tuple[Evidence, ...]
    raw_value: str | None = None
    reference_event: str | None = None
    conditions: tuple[str, ...] = ()
    minimum_value: str | None = None
    maximum_value: str | None = None


@dataclass(frozen=True)
class ExtractionRun:
    """One extractor's facts, validation problems and run information."""

    fields: dict[str, ExtractedField]
    issues: tuple[str, ...]
    metadata: dict
    raw_response: str | None = None


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError(f"nonfinite JSON value: {value}")


def parse_json(text: str):
    """Decode run, model or review JSON without duplicate keys or nonfinite numbers."""
    return json.loads(text, object_pairs_hook=_unique_keys, parse_constant=_reject_constant)


def read_fact(data: dict) -> ExtractedField:
    """Check JSON types before constructing the common Python record."""
    required = {"value", "status", "raw_value", "reference_event", "conditions",
                "minimum_value", "maximum_value", "evidence"}
    if not isinstance(data, dict) or set(data) != required:
        raise ValueError("fact keys do not match the schema")
    for name in ("value", "raw_value", "reference_event", "minimum_value", "maximum_value"):
        if data[name] is not None and not isinstance(data[name], str):
            raise ValueError(f"{name} must be text or null")
    if data["status"] not in STATUSES:
        raise ValueError("unknown extraction status")
    if not isinstance(data["conditions"], list) or not all(isinstance(item, str) and item.strip() for item in data["conditions"]):
        raise ValueError("conditions must be a list of nonempty text")
    if not isinstance(data["evidence"], list):
        raise ValueError("evidence must be a list")
    evidence = []
    for excerpt in data["evidence"]:
        if (not isinstance(excerpt, dict) or set(excerpt) != {"page_number", "text"}
                or type(excerpt["page_number"]) is not int or excerpt["page_number"] < 1
                or not isinstance(excerpt["text"], str)):
            raise ValueError("invalid evidence entry")
        evidence.append(Evidence(excerpt["page_number"], excerpt["text"]))
    return ExtractedField(data["value"], data["status"], tuple(evidence),
                          data["raw_value"], data["reference_event"], tuple(data["conditions"]),
                          data["minimum_value"], data["maximum_value"])


def read_number(value: str, name: str) -> Decimal:
    """Read a bounded decimal string without guessing malformed separators."""
    if not isinstance(value, str) or not re.fullmatch(r"(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]+)?", value):
        raise ValueError("expected an unsigned decimal string")
    try:
        number = Decimal(value.replace(",", ""))
        if not number.is_finite() or number >= Decimal("1e12") or number.as_tuple().exponent < -6:
            raise ValueError("number exceeds supported size or precision")
        if name in WHOLE_NUMBER_FIELDS and number != number.to_integral_value():
            raise ValueError("expected a whole number")
        if name == "quantity" and number == 0:
            raise ValueError("quantity must be positive")
        return number
    except InvalidOperation as error:
        raise ValueError("invalid decimal") from error


PERCENT_FIELDS = ("vat_rate", "advance_percent", "penalty_percent")
DURATION_FIELDS = ("payment_days", "delivery_days", "validity_days")


def locate_excerpt(text: str, page_text: str) -> str | None:
    """Return the exact page text a quote refers to, or None if it is not in the page.

    Only whitespace may differ (a space where the page has a line break). Words,
    digits and punctuation must match, so an invented quote is still refused."""
    if text.strip() and text in page_text:
        return text
    words = text.split()
    if not words:
        return None
    match = re.search(r"\s+".join(re.escape(word) for word in words), page_text)
    return match.group(0) if match else None


def clean_unit_marker(name: str, value: str, raw_value: str | None) -> str:
    """Drop a '%' or 'days' marker, but only if the printed text has the same number.

    '15%' with raw '15%' becomes '15'; raw_value keeps the printed wording. Any other
    mismatch is left alone so the strict number check still rejects it."""
    if name in PERCENT_FIELDS:
        match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*%", value.strip())
    elif name in DURATION_FIELDS:
        match = re.fullmatch(r"([0-9]+)\s*days?", value.strip(), re.I)
    else:
        return value
    if match and raw_value and re.search(r"(?<![0-9.,])" + re.escape(match.group(1)) + r"(?![0-9])", raw_value):
        return match.group(1)
    return value


def explicit_penalty_absence(evidence: tuple[Evidence, ...]) -> bool:
    """A missing extraction alone cannot establish absence of a penalty."""
    pattern = (r"\bno (?:late delivery )?penalty(?: applies|required)?[.\s]*$"
               r"|\b(?:penalty|delay)\s*:\s*(?:none|not applicable)[.\s]*$")
    return any(re.search(pattern, excerpt.text, re.I) for excerpt in evidence)


def validate_fields(fields: dict[str, ExtractedField], document: PdfDocument) -> ExtractionRun:
    """Check source traceability and data consistency, not semantic truth."""
    pages = {page.page_number: page.text for page in document.pages}
    checked, issues = {}, []
    for name in FACT_NAMES:
        fact = fields.get(name, ExtractedField(None, "not_found", ()))
        try:
            if fact.status not in STATUSES:
                raise ValueError("unknown extraction status")
            if fact.status == "found" and (not isinstance(fact.value, str) or not fact.value.strip()):
                raise ValueError("found requires a nonempty value")
            if fact.status != "found" and fact.value is not None:
                raise ValueError("unresolved facts must have a null value")
            if fact.status == "found" and not fact.evidence:
                raise ValueError("found requires source evidence")
            # A malformed quote is an error. A quote that is not in the page is
            # dropped; the fact survives only if some quote is really in the page.
            resolved = []
            for excerpt in fact.evidence:
                if (type(excerpt.page_number) is not int or excerpt.page_number not in pages
                        or not isinstance(excerpt.text, str) or not excerpt.text.strip()):
                    raise ValueError("evidence does not match an original page")
                exact = locate_excerpt(excerpt.text, pages[excerpt.page_number])
                if exact is not None:
                    resolved.append(Evidence(excerpt.page_number, exact))
            if fact.evidence and not resolved:
                raise ValueError("evidence does not match an original page")
            fact = replace(fact, evidence=tuple(resolved))
            if name in NUMERIC_FIELDS and fact.value is not None:
                fact = replace(fact, value=clean_unit_marker(name, fact.value, fact.raw_value))
                read_number(fact.value, name)
            bounds = (fact.minimum_value, fact.maximum_value)
            if any(value is not None for value in bounds):
                if name not in NUMERIC_FIELDS or any(value is None for value in bounds):
                    raise ValueError("numeric bounds require both endpoints")
                lower, upper = (read_number(value, name) for value in bounds)
                if lower > upper:
                    raise ValueError("minimum exceeds maximum")
                if fact.value is not None and not lower <= read_number(fact.value, name) <= upper:
                    raise ValueError("value lies outside its bounds")
            if name == "penalty_clause" and fact.value == "absent" and not explicit_penalty_absence(fact.evidence):
                raise ValueError("penalty absence requires an explicit source statement")
            checked[name] = fact
        except ValueError as error:
            # Keep original source excerpts only if they really exist; do not
            # display a model's invented citation as document evidence.
            valid_evidence = tuple(
                Evidence(excerpt.page_number, exact) for excerpt in fact.evidence
                if type(excerpt.page_number) is int and excerpt.page_number in pages
                and isinstance(excerpt.text, str) and excerpt.text.strip()
                and (exact := locate_excerpt(excerpt.text, pages[excerpt.page_number])) is not None)
            checked[name] = replace(fact, value=None, status="unrecognized", evidence=valid_evidence)
            issues.append(f"{name}: {error}")
    for kind in ("payment", "delivery", "validity"):
        name = kind + "_days"
        fact, reference = checked[name], checked[kind + "_reference"]
        if fact.status == "found" and reference.status == "found" and fact.reference_event != reference.value:
            checked[name] = replace(fact, value=None, status="unrecognized")
            issues.append(f"{name}: conflicting reference events")
    # Source geometry is independent evidence: a model's row count cannot hide
    # a second recognized item row, even when both rows have identical values.
    item_tables = []
    for page in document.pages:
        for table in page.tables:
            columns = item_columns(table)
            if (columns and {'description', 'quantity'} <= set(columns)
                    and ('unit_price' in columns or 'line_amount' in columns)):
                item_tables.append(table)
    row_count = sum(len(table.rows) for table in item_tables)
    if item_tables and row_count != 1:
        issues.append(f'This workflow requires exactly one item across detected item tables; found {row_count}.')
        for name in ('item_code', 'description', 'quantity', 'unit', 'unit_price', 'line_amount'):
            checked[name] = replace(checked[name], value=None, status='unrecognized')
    return ExtractionRun(checked, tuple(issues), {})


def resolve_field(candidates: list, unsupported: list) -> ExtractedField:
    """Keep one agreed value, or explain why extraction needs attention."""
    evidence = tuple(excerpt for value, excerpt in candidates) + tuple(unsupported)
    if unsupported:
        return ExtractedField(None, "unrecognized", evidence)
    values = {value for value, excerpt in candidates}
    if not values:
        return ExtractedField(None, "not_found", ())
    if len(values) > 1:
        return ExtractedField(None, "ambiguous", evidence)
    return ExtractedField(candidates[0][0], "found", evidence)


def preview(extractor, required_fields: tuple) -> int:
    """One terminal preview shared by the three extractors."""
    parser = argparse.ArgumentParser(description=extractor.__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    needs_attention = False
    for path in parser.parse_args().paths:
        try:
            document = read_pdf(path)
        except PdfReadError as error:
            print(f"Extraction error: {error}", file=sys.stderr)
            needs_attention = True
            continue
        print(f"\nPDF: {document.source_path.name}")
        for issue in document.issues:
            print(f"Extraction issue: {issue}")
            needs_attention = True
        for name, field in extractor(document).items():
            print(f"{name}: {field.value if field.status == 'found' else field.status}")
            for evidence in field.evidence:
                print(f"  Page {evidence.page_number}: {evidence.text!r}")
            if field.status in ("unrecognized", "ambiguous"):
                needs_attention = True
            if name in required_fields and field.status != "found":
                needs_attention = True
    return int(needs_attention)
