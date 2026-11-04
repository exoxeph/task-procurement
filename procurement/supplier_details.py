"""Block 3: extract supplier and quotation facts using explicit text patterns."""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

from procurement.extraction import Evidence, ExtractedField
from procurement.pdf_text import PdfDocument, PdfReadError, read_pdf


# These patterns locate labels, not expected answers or supplier filenames.
# ^ means start of a line; [ \t]* permits spaces; \b means a word boundary.
FIELD_LABELS = {
    "quotation_number": r"^[ \t]*Quotation[ \t]+(?:no\.?|number|#)(?=[ \t:\r\n]|$)",
    "quotation_date": r"^[ \t]*(?:Quotation[ \t]+)?Date\b",
    "purchase_request_reference": r"^[ \t]*(?:Purchase[ \t]+request[ \t]+)?Reference\b",
    # Require a colon or line end so ordinary words like "tin 123" do not match.
    "tin": r"\bTIN(?=[ \t]*:|[ \t]*$)",
    "bin": r"\bBIN(?=[ \t]*:|[ \t]*$)",
}


def _resolve_field(candidates: list, unsupported: list) -> ExtractedField:
    """Keep a value only when all occurrences are supported and agree."""
    evidence = tuple(excerpt for value, excerpt in candidates) + tuple(unsupported)
    if unsupported:
        return ExtractedField(value=None, status="unrecognized", evidence=evidence)

    values = {value for value, excerpt in candidates}
    if not values:
        return ExtractedField(value=None, status="not_found", evidence=())
    if len(values) > 1:
        return ExtractedField(value=None, status="ambiguous", evidence=evidence)

    return ExtractedField(value=candidates[0][0], status="found", evidence=evidence)


def _value_is_supported(field_name: str, value: str) -> bool:
    """Check parser formats, without claiming legal registration validation."""
    if field_name == "quotation_date":
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            return False
        try:
            date.fromisoformat(value)
        except ValueError:
            return False
        return True

    if field_name in ("tin", "bin"):
        return re.fullmatch(r"[0-9]+(?:-[0-9]+)*", value) is not None

    # Quote and purchase-request identifiers must include at least one digit.
    valid_characters = re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9./_-]*", value)
    return valid_characters is not None and any(character.isdigit() for character in value)


def _extract_labelled_field(document: PdfDocument, field_name: str) -> ExtractedField:
    """Find every occurrence of one label and inspect its following token."""
    candidates = []
    unsupported = []
    label_pattern = re.compile(FIELD_LABELS[field_name], re.IGNORECASE | re.MULTILINE)

    for page in document.pages:
        for label in label_pattern.finditer(page.text):
            remaining_text = page.text[label.end():]
            # A value may follow a colon, spaces, or a line break.
            value_match = re.match(r"[ \t\r\n]*:?[ \t\r\n]*(?P<value>\S+)", remaining_text)
            if value_match is None:
                unsupported.append(Evidence(page.page_number, label.group()))
                continue

            value = value_match.group("value")
            end_position = label.end() + value_match.end()
            excerpt = Evidence(page.page_number, page.text[label.start():end_position])

            if _value_is_supported(field_name, value):
                candidates.append((value, excerpt))
            else:
                unsupported.append(excerpt)

    return _resolve_field(candidates, unsupported)


def _extract_supplier_name(document: PdfDocument) -> ExtractedField:
    """Use explicit supplier labels, quotation headings, and For signoffs."""
    candidates = []
    unsupported = []

    for page in document.pages:
        lines = page.text.splitlines()
        for index, line in enumerate(lines):
            labelled_name = re.fullmatch(
                r"[ \t]*Supplier(?:[ \t]+name)?[ \t]*:[ \t]*(?P<value>.*)",
                line, flags=re.IGNORECASE,
            )
            if labelled_name:
                value = labelled_name.group("value").strip()
                if value:
                    candidates.append((value, Evidence(page.page_number, line)))
                else:
                    unsupported.append(Evidence(page.page_number, line))

            # In this baseline template, the supplier is above QUOTATION.
            if line.strip().casefold() == "quotation":
                previous = index - 1
                while previous >= 0 and not lines[previous].strip():
                    previous -= 1
                if previous >= 0:
                    raw_name = lines[previous]
                    candidates.append((raw_name.strip(), Evidence(page.page_number, raw_name)))

            signoff = re.fullmatch(r"[ \t]*For[ \t]+(?P<value>.+)", line, flags=re.IGNORECASE)
            if signoff:
                value = signoff.group("value").strip()
                if value:
                    candidates.append((value, Evidence(page.page_number, line)))

    return _resolve_field(candidates, unsupported)


def extract_supplier_details(document: PdfDocument) -> dict[str, ExtractedField]:
    """Return six fields; the caller also retains the original document issues."""
    fields = {"supplier_name": _extract_supplier_name(document)}
    for field_name in FIELD_LABELS:
        fields[field_name] = _extract_labelled_field(document, field_name)
    return fields


def main() -> int:
    """Preview extracted fields and evidence without making policy decisions."""
    parser = argparse.ArgumentParser(description="Extract supplier details with page evidence.")
    parser.add_argument("paths", nargs="+", type=Path, help="PDF files to inspect.")
    arguments = parser.parse_args()
    needs_attention = False

    for path in arguments.paths:
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

        fields = extract_supplier_details(document)
        for name, field in fields.items():
            if field.status == "found":
                print(f"{name}: {field.value}")
            else:
                print(f"{name}: {field.status}")
                needs_attention = True
            for evidence in field.evidence:
                print(f"  Page {evidence.page_number}: {evidence.text!r}")

    if needs_attention:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
