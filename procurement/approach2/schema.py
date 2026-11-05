"""The AI response contract and readable local validation; no model calls here."""

from dataclasses import replace

from procurement.shared.extraction import (
    ExtractedField, ExtractionRun, FACT_NAMES, STATUSES, parse_json, read_fact, validate_fields,
)
from procurement.shared.pdf_text import PdfDocument


SCHEMA_VERSION = "1"
NULLABLE_TEXT = {"type": ["string", "null"]}
FACT_PROPERTIES = {
    "value": NULLABLE_TEXT,
    "status": {"type": "string", "enum": list(STATUSES)},
    "raw_value": NULLABLE_TEXT,
    "reference_event": NULLABLE_TEXT,
    "conditions": {"type": "array", "items": {"type": "string"}},
    "minimum_value": NULLABLE_TEXT,
    "maximum_value": NULLABLE_TEXT,
    "evidence": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "properties": {"page_number": {"type": "integer", "minimum": 1}, "text": {"type": "string"}},
        "required": ["page_number", "text"],
    }},
}
FACT_SCHEMA = {"type": "object", "properties": FACT_PROPERTIES,
               "required": list(FACT_PROPERTIES), "additionalProperties": False}
OUTPUT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "$defs": {"fact": FACT_SCHEMA},
    "properties": {
        "fields": {"type": "object", "properties": {name: {"$ref": "#/$defs/fact"} for name in FACT_NAMES},
                   "required": list(FACT_NAMES), "additionalProperties": False},
        "issues": {"type": "array", "items": {"type": "string"}},
        "item_count": {"type": "integer", "minimum": 0},
    },
    "required": ["fields", "issues", "item_count"],
}


def validate_response(payload: dict, document: PdfDocument) -> ExtractionRun:
    """Reject broken documents; retain individual fact errors as review issues."""
    if not isinstance(payload, dict) or set(payload) != {"fields", "issues", "item_count"}:
        raise ValueError("response keys do not match the schema")
    if not isinstance(payload["fields"], dict) or set(payload["fields"]) != set(FACT_NAMES):
        raise ValueError("response must include exactly the required facts")
    if type(payload["item_count"]) is not int or payload["item_count"] < 0:
        raise ValueError("item_count must be a nonnegative integer")
    if not isinstance(payload["issues"], list) or not all(isinstance(item, str) and item.strip() for item in payload["issues"]):
        raise ValueError("issues must be a list of nonempty text")
    fields, issues = {}, list(payload["issues"])
    if payload["item_count"] != 1:
        issues.append("This workflow requires exactly one item; do not select one row from multiple items.")
    for name, data in payload["fields"].items():
        try:
            fields[name] = read_fact(data)
        except ValueError as error:
            fields[name] = ExtractedField(None, "unrecognized", ())
            issues.append(f"{name}: {error}")
    run = validate_fields(fields, document)
    if payload['item_count'] != 1:
        # A flat one-item contract cannot safely represent a chosen row from
        # multiple items, even when that row has genuine source evidence.
        for name in ('item_code', 'description', 'quantity', 'unit', 'unit_price', 'line_amount'):
            run.fields[name] = replace(run.fields[name], value=None, status='unrecognized')
    return replace(run, issues=tuple(issues) + run.issues, metadata={"schema_version": SCHEMA_VERSION})


def parse_response(text: str, document: PdfDocument) -> ExtractionRun:
    """Parse JSON without accepting duplicate keys, NaN or Infinity."""
    payload = parse_json(text)
    return replace(validate_response(payload, document), raw_response=text)
