"""Block 4: extract stated item/financial facts, without checking their arithmetic."""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from procurement.extraction import Evidence, ExtractedField
from procurement.pdf_text import PdfDocument, PdfPage, PdfReadError, read_pdf


ITEM_FIELDS = ("item_code", "description", "quantity", "unit", "unit_price", "line_amount")
FIELD_NAMES = ITEM_FIELDS + ("subtotal", "vat_rate", "vat_amount", "total", "unit_price_tax_note")
REQUIRED_FIELDS = ITEM_FIELDS + ("total",)

# Full-token matching prevents accepting only part of a malformed amount.
INTEGER = r"(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)"
NUMBER = INTEGER + r"(?:\.[0-9]+)?"


@dataclass(frozen=True)
class _TextLine:
    """A nonempty line and its original positions in the page text."""

    text: str
    start: int
    end: int


def _page_lines(text: str) -> list[_TextLine]:
    """Ignore blank lines for matching, but keep offsets for exact evidence."""
    lines = []
    position = 0
    for raw_line in text.splitlines(keepends=True):
        if raw_line.strip():
            lines.append(_TextLine(raw_line.strip(), position, position + len(raw_line)))
        position += len(raw_line)
    return lines


def _resolve_field(candidates: list, unsupported: list) -> ExtractedField:
    """Use the same status rules as Block 3, retaining every source occurrence."""
    evidence = tuple(excerpt for value, excerpt in candidates) + tuple(unsupported)
    if unsupported:
        return ExtractedField(None, "unrecognized", evidence)
    values = {value for value, excerpt in candidates}
    if not values:
        return ExtractedField(None, "not_found", ())
    if len(values) > 1:
        return ExtractedField(None, "ambiguous", evidence)
    return ExtractedField(candidates[0][0], "found", evidence)


def _header_end(lines: list[_TextLine], start: int) -> int | None:
    """Locate the last header line, including pack 10's shared final headers."""
    first_headers = [line.text.casefold() for line in lines[start:start + 4]]
    if first_headers != ["item", "description", "qty", "unit"]:
        return None
    if start + 4 >= len(lines):
        return None

    price_header = lines[start + 4].text
    pattern = (
        r"Unit price[ \t]*\(BDT(?:,[ \t]*VAT[ \t]+(?:included|excluded))?\)"
        r"(?P<amount_header>[ \t]+Amount[ \t]*\(BDT\))?"
    )
    match = re.fullmatch(pattern, price_header, flags=re.IGNORECASE)
    if match is None:
        return None
    if match.group("amount_header"):
        return start + 4
    if start + 5 < len(lines) and lines[start + 5].text.casefold() == "amount (bdt)":
        return start + 5
    return None


def _item_values(body: list[_TextLine], page_text: str) -> dict | None:
    """Read one item; reject unsupported rows instead of guessing columns."""
    if len(body) < 6:
        return None

    # The last four cells are quantity, unit, unit price, and line amount.
    description_lines = body[1:-4]
    if any(re.fullmatch(NUMBER, line.text) for line in description_lines):
        # This can indicate an extra item row; numeric-only description lines
        # are also outside this deliberately conservative baseline format.
        return None

    values = {
        "item_code": body[0].text,
        "description": page_text[description_lines[0].start:description_lines[-1].end].strip(),
        "quantity": body[-4].text,
        "unit": body[-3].text,
        "unit_price": body[-2].text,
        "line_amount": body[-1].text,
    }
    valid = (
        re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", values["item_code"])
        and any(character.isalpha() for character in values["description"])
        and re.fullmatch(INTEGER, values["quantity"])
        and re.fullmatch(r"[A-Za-z][A-Za-z0-9 /_-]*", values["unit"])
        and re.fullmatch(NUMBER, values["unit_price"])
        and re.fullmatch(NUMBER, values["line_amount"])
    )
    if not valid:
        return None
    return values


def _summary_value(text: str, label_pattern: str) -> str | None:
    """Recognize a summary label, not a description that starts with its word."""
    label = re.match(label_pattern, text, flags=re.IGNORECASE)
    if label is None:
        return None
    remaining = text[label.end():].strip()
    if not remaining:
        return ""  # The amount should be on the next nonempty line.
    if remaining.startswith(":"):
        return remaining[1:].strip()
    if re.match(r"[+-]?[0-9]", remaining):
        return remaining  # Includes malformed numeric tokens for validation.
    return None


def _is_vat_label(text: str) -> bool:
    """Keep ordinary descriptions such as 'VAT resistant fabric' out of totals."""
    starts_like_label = re.match(r"^VAT(?:[ \t]*:|[ \t]*$|[ \t]+[+-]?[0-9])", text, re.IGNORECASE)
    has_rate_marker = re.match(r"^VAT\b", text, re.IGNORECASE) and "%" in text
    return bool(starts_like_label or has_rate_marker)


def _collect_item_tables(page: PdfPage, lines: list, candidates: dict, unsupported: dict) -> set[int]:
    """Collect supported tables, retaining the complete table as field evidence."""
    table_lines = set()
    for start, line in enumerate(lines):
        if line.text.casefold() != "item":
            continue

        header_end = _header_end(lines, start)
        if header_end is None:
            last = min(start + 5, len(lines) - 1)
            table_lines.update(range(start, last + 1))
            excerpt = Evidence(page.page_number, page.text[line.start:lines[last].end])
            for name in ITEM_FIELDS + ("unit_price_tax_note",):
                unsupported[name].append(excerpt)
            continue

        end = header_end + 1
        while end < len(lines):
            text = lines[end].text
            is_summary = (
                _summary_value(text, r"Subtotal\b") is not None
                or _summary_value(text, r"Total\b(?:[ \t]*\([^)]*\))?") is not None
                or _is_vat_label(text)
            )
            section = r"^(?:Supplier[ \t]+(?:TIN\b|BIN\b|registration\b)|TERMS AND CONDITIONS\b|Item$)"
            if is_summary or re.match(section, text, flags=re.IGNORECASE):
                break
            end += 1

        table_lines.update(range(start, end))
        body = lines[header_end + 1:end]
        last = end - 1 if body else header_end
        excerpt = Evidence(page.page_number, page.text[line.start:lines[last].end])
        values = _item_values(body, page.text)
        if values is None:
            for name in ITEM_FIELDS + ("unit_price_tax_note",):
                unsupported[name].append(excerpt)
            continue

        for name, value in values.items():
            candidates[name].append((value, excerpt))

        price_header = lines[start + 4]
        tax_note = re.search(r"\bVAT[ \t]+(?:included|excluded)\b", price_header.text, flags=re.IGNORECASE)
        if tax_note:
            note_evidence = Evidence(page.page_number, page.text[price_header.start:price_header.end])
            candidates["unit_price_tax_note"].append((tax_note.group(), note_evidence))

    return table_lines


def _collect_amount(
    name: str, inline_value: str, page: PdfPage, lines: list, index: int,
    candidates: dict, unsupported: dict,
) -> None:
    """Read a full amount on the label line or the following nonempty line."""
    value = inline_value.strip()
    last = index
    if not value and index + 1 < len(lines):
        last = index + 1
        value = lines[last].text

    excerpt = Evidence(page.page_number, page.text[lines[index].start:lines[last].end])
    if re.fullmatch(NUMBER, value):
        candidates[name].append((value, excerpt))
    else:
        unsupported[name].append(excerpt)


def _collect_totals(
    page: PdfPage, lines: list, candidates: dict, unsupported: dict, table_lines: set[int],
) -> None:
    """Read explicit subtotal, VAT, and total labels without calculating values."""
    for index, line in enumerate(lines):
        if index in table_lines:
            continue  # Item descriptions are not financial summary entries.
        for name, pattern in (
            ("subtotal", r"Subtotal\b"),
            ("total", r"Total\b(?:[ \t]*\([^)]*\))?"),
        ):
            value = _summary_value(line.text, pattern)
            if value is not None:
                _collect_amount(name, value, page, lines, index, candidates, unsupported)

        if not _is_vat_label(line.text):
            continue
        vat = re.fullmatch(
            rf"VAT[ \t]+(?P<rate>{NUMBER})[ \t]*%[ \t]*:?[ \t]*(?P<value>.*)",
            line.text, flags=re.IGNORECASE,
        )
        excerpt = Evidence(page.page_number, page.text[line.start:line.end])
        if vat is None:
            unsupported["vat_rate"].append(excerpt)
            unsupported["vat_amount"].append(excerpt)
            continue

        candidates["vat_rate"].append((vat.group("rate"), excerpt))
        _collect_amount("vat_amount", vat.group("value"), page, lines, index, candidates, unsupported)


def extract_financial_details(document: PdfDocument) -> dict[str, ExtractedField]:
    """Extract raw facts; callers must retain the original document issues too."""
    candidates = {name: [] for name in FIELD_NAMES}
    unsupported = {name: [] for name in FIELD_NAMES}

    for page in document.pages:
        lines = _page_lines(page.text)
        table_lines = _collect_item_tables(page, lines, candidates, unsupported)
        _collect_totals(page, lines, candidates, unsupported, table_lines)

    return {
        name: _resolve_field(candidates[name], unsupported[name])
        for name in FIELD_NAMES
    }


def main() -> int:
    """Preview extraction, not financial correctness or supplier approval."""
    parser = argparse.ArgumentParser(description="Extract item and financial details with evidence.")
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

        fields = extract_financial_details(document)
        for name, field in fields.items():
            print(f"{name}: {field.value if field.status == 'found' else field.status}")
            for evidence in field.evidence:
                print(f"  Page {evidence.page_number}: {evidence.text!r}")
            if field.status in ("unrecognized", "ambiguous"):
                needs_attention = True
            if name in REQUIRED_FIELDS and field.status != "found":
                needs_attention = True

    if needs_attention:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
