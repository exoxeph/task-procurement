"""The AI response contract and readable local validation; no model calls here."""

from dataclasses import replace

from procurement.shared.extraction import (
    ExtractedField, ExtractionRun, FACT_NAMES, STATUSES, parse_json, read_fact, validate_fields,
)
from procurement.shared.pdf_text import PdfDocument


SCHEMA_VERSION = "3"
NULLABLE_TEXT = {"type": ["string", "null"]}
EVENTS = ["delivery", "purchase_order", "quotation_date", "invoice", "other"]
WHOLE_NUMBER = r"^[0-9]+$"
DECIMAL_NUMBER = r"^[0-9]+(\.[0-9]+)?$"
ISO_DATE = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
NULL_ONLY = {"type": "null"}


def ref(name):
    return {"$ref": "#/$defs/" + name}


# Pieces shared by every fact shape, so the schema stays small enough to send.
PARTS = {
    "evidence": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "properties": {"page_number": {"type": "integer", "minimum": 1}, "text": {"type": "string"}},
        "required": ["page_number", "text"],
    }},
    "status": {"type": "string", "enum": list(STATUSES)},
    "conditions": {"type": "array", "items": {"type": "string"}},
    "whole_number": {"type": ["string", "null"], "pattern": WHOLE_NUMBER},
    "decimal_number": {"type": ["string", "null"], "pattern": DECIMAL_NUMBER},
    "iso_date": {"type": ["string", "null"], "pattern": ISO_DATE},
    "event": {"type": ["string", "null"], "enum": EVENTS + [None]},
    "penalty": {"type": ["string", "null"], "enum": ["present", "absent", None]},
}


def fact_shape(value, *, event=NULL_ONLY, bound=NULL_ONLY):
    """One fact shape. Property order is the model's writing order: quote the
    source and copy the printed text first, so the cleaned value derives from them."""
    return {"type": "object", "additionalProperties": False,
            "properties": {
                "evidence": ref("evidence"),
                "status": ref("status"),
                "raw_value": NULLABLE_TEXT,
                "value": value,
                "reference_event": event,
                "conditions": ref("conditions"),
                "minimum_value": bound,
                "maximum_value": bound,
            },
            "required": ["evidence", "status", "raw_value", "value", "reference_event",
                         "conditions", "minimum_value", "maximum_value"]}


# Format rules are enforced while the model writes, not only checked afterwards.
# Nothing here encodes company policy: only the shapes the shared contract accepts.
FACT_DEFS = {
    **PARTS,
    "text_fact": fact_shape(NULLABLE_TEXT),
    "date_fact": fact_shape(ref("iso_date")),
    "whole_number_fact": fact_shape(ref("whole_number")),
    "decimal_fact": fact_shape(ref("decimal_number")),
    "duration_fact": fact_shape(ref("whole_number"), event=ref("event"), bound=ref("whole_number")),
    "event_fact": fact_shape(ref("event")),
    "penalty_clause_fact": fact_shape(ref("penalty")),
}
FACT_KINDS = {
    "quotation_date": "date_fact", "quantity": "whole_number_fact",
    "unit_price": "decimal_fact", "line_amount": "decimal_fact", "subtotal": "decimal_fact",
    "vat_rate": "decimal_fact", "vat_amount": "decimal_fact", "total": "decimal_fact",
    "advance_percent": "decimal_fact", "penalty_percent": "decimal_fact",
    "payment_days": "duration_fact", "delivery_days": "duration_fact", "validity_days": "duration_fact",
    "payment_reference": "event_fact", "delivery_reference": "event_fact", "validity_reference": "event_fact",
    "penalty_clause": "penalty_clause_fact",
}
def _writing_order():
    """Write each reference event right after the duration it explains, while the
    model is still looking at that clause. Key order is not part of the contract."""
    moved = {kind + "_reference" for kind in ("payment", "delivery", "validity")}
    order = [name for name in FACT_NAMES if name not in moved]
    for kind in ("payment", "delivery", "validity"):
        order.insert(order.index(kind + "_days") + 1, kind + "_reference")
    return order


WRITING_ORDER = _writing_order()
OUTPUT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "$defs": FACT_DEFS,
    "properties": {
        "fields": {"type": "object",
                   "properties": {name: {"$ref": "#/$defs/" + FACT_KINDS.get(name, "text_fact")}
                                  for name in WRITING_ORDER},
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
