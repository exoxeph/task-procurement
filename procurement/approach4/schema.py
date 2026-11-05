"""Approach 4 extractor contract: approach 3's typed facts plus a short 'notes' line written first.

Validation here ANNOTATES instead of erasing. A fact the extractor marked found that fails a
code check (quote not in the page, bad format, event conflict) keeps its value and gets a
warning, so the judge agent sees both the value and the doubt. The strict, erasing view is
still computed and is what the Python rules use as their independent check.
"""

from copy import deepcopy

from procurement.approach3 import schema as base
from procurement.shared.extraction import ExtractionRun, FACT_NAMES, parse_json, read_fact

SCHEMA_VERSION = "4"


def _with_notes(shape):
    shape = deepcopy(shape)
    shape["properties"] = {"notes": {"type": "string"}, **shape["properties"]}
    shape["required"] = ["notes"] + shape["required"]
    return shape


FACT_DEFS = {name: _with_notes(definition) if name.endswith("_fact") else definition
             for name, definition in base.FACT_DEFS.items()}
OUTPUT_SCHEMA = {**deepcopy(base.OUTPUT_SCHEMA), "$defs": FACT_DEFS}


def parse_response(text: str, document) -> ExtractionRun:
    """Return the extractor's facts with warnings attached; never erase a found value."""
    payload = parse_json(text)
    if not isinstance(payload, dict) or set(payload) != {"fields", "issues", "item_count"}:
        raise ValueError("response keys do not match the schema")
    if not isinstance(payload["fields"], dict) or set(payload["fields"]) != set(FACT_NAMES):
        raise ValueError("response must include exactly the required facts")
    notes, stripped = {}, {}
    for name, data in payload["fields"].items():
        if isinstance(data, dict) and "notes" in data:
            data = dict(data)
            notes[name] = data.pop("notes")
        stripped[name] = data
    strict = base.validate_response({**payload, "fields": stripped}, document)
    kept, warnings = {}, {}
    for name, data in stripped.items():
        try:
            original = read_fact(data)
        except ValueError:
            original = None
        checked = strict.fields[name]
        if original is not None and original.status == "found" and checked.status != "found":
            kept[name] = original
            reasons = [issue.split(": ", 1)[1] for issue in strict.issues if issue.startswith(name + ": ")]
            warnings[name] = reasons or ["failed a code check"]
        else:
            kept[name] = checked
    metadata = {"schema_version": SCHEMA_VERSION, "notes": notes, "warnings": warnings}
    return ExtractionRun(kept, strict.issues, metadata, text)
