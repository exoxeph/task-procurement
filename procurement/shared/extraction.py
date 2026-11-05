"""Small records shared by the baseline's document extraction steps."""

from dataclasses import dataclass
import argparse
from pathlib import Path
import sys

from procurement.shared.pdf_text import PdfReadError, read_pdf


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
