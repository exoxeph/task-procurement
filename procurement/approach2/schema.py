"""The AI response contract and readable local validation; no model calls here."""

from dataclasses import replace
import json

from procurement.shared.extraction import (
    Evidence, ExtractedField, ExtractionRun, FACT_NAMES, STATUSES, validate_fields,
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


def _read_fact(data: dict) -> ExtractedField:
    """Check JSON types before constructing the common Python record."""
    if not isinstance(data, dict) or set(data) != set(FACT_PROPERTIES):
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
            fields[name] = _read_fact(data)
        except ValueError as error:
            fields[name] = ExtractedField(None, "unrecognized", ())
            issues.append(f"{name}: {error}")
    run = validate_fields(fields, document)
    return replace(run, issues=tuple(issues) + run.issues, metadata={"schema_version": SCHEMA_VERSION})


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError(f"nonfinite JSON value: {value}")


def parse_response(text: str, document: PdfDocument) -> ExtractionRun:
    """Parse JSON without accepting duplicate keys, NaN or Infinity."""
    payload = json.loads(text, object_pairs_hook=_unique_keys, parse_constant=_reject_constant)
    return replace(validate_response(payload, document), raw_response=text)
