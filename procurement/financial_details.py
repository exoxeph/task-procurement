"""Read the stated item and money figures in the supported single-item template."""

import re

from procurement.extraction import Evidence, ExtractedField, preview, resolve_field
from procurement.pdf_text import PdfDocument


ITEM_FIELDS = ("item_code", "description", "quantity", "unit", "unit_price", "line_amount")
FIELD_NAMES = ITEM_FIELDS + ("subtotal", "vat_rate", "vat_amount", "total", "unit_price_tax_note")
REQUIRED_FIELDS = ITEM_FIELDS + ("total",)
INTEGER = r"(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)"
NUMBER = INTEGER + r"(?:\.[0-9]+)?"

# Labels stand alone, have a colon, or are followed by a numeric token.
# Ordinary descriptions such as 'Total protection fabric' do not match.
SUMMARY = re.compile(
    r"^(?P<label>Subtotal|Total(?:[ \t]*\([^)]*\))?)"
    r"(?:[ \t]*:[ \t]*(?P<colon>.*)|[ \t]+(?P<inline>[+-]?[0-9].*)|[ \t]*)$", re.I,
)
VAT_LABEL = re.compile(r"^VAT(?:[ \t]*:|[ \t]*$|[ \t]+[+-]?[0-9]|\b.*%)", re.I)
SECTION = re.compile(r"^(?:Supplier\s+(?:TIN\b|BIN\b|registration\b)|TERMS AND CONDITIONS\b|Item$)", re.I)


def _read_table(texts: list[str]) -> dict | None:
    """Read headers, then code / description / quantity / unit / price / amount."""
    if [text.casefold() for text in texts[:4]] != ["item", "description", "qty", "unit"]:
        return None
    if len(texts) < 5:
        return None
    price_header = texts[4]
    if not re.fullmatch(
        r"Unit price\s*\(BDT(?:,\s*VAT\s+(?:included|excluded))?\)(?:\s+Amount\s*\(BDT\))?",
        price_header, re.I,
    ):
        return None
    body_start = 5
    if "amount" not in price_header.casefold():
        if len(texts) < 6 or texts[5].casefold() != "amount (bdt)":
            return None
        body_start = 6
    body = texts[body_start:]
    if len(body) < 6:
        return None
    description = body[1:-4]
    if any(re.fullmatch(NUMBER, line) for line in description):
        return None  # A numeric-only description may actually be another item row.
    values = dict(zip(ITEM_FIELDS, (body[0], "\n".join(description), *body[-4:])))
    patterns = {"item_code": r"[A-Za-z0-9][A-Za-z0-9_-]*", "quantity": INTEGER,
                "unit": r"[A-Za-z][A-Za-z0-9 /_-]*", "unit_price": NUMBER, "line_amount": NUMBER}
    if not any(letter.isalpha() for letter in values["description"]):
        return None
    for name, pattern in patterns.items():
        if not re.fullmatch(pattern, values[name]):
            return None
    note = re.search(r"VAT\s+(?:included|excluded)", price_header, re.I)
    if note:
        values["unit_price_tax_note"] = note.group()
    return values


def extract_financial_details(document: PdfDocument) -> dict[str, ExtractedField]:
    """Walk each page in order: read tables, then read labelled financial totals."""
    candidates = {name: [] for name in FIELD_NAMES}
    unsupported = {name: [] for name in FIELD_NAMES}
    for page in document.pages:
        # Match objects provide original positions without a separate line class.
        lines = list(re.finditer(r"^[^\S\r\n]*\S[^\r\n]*", page.text, re.M))
        texts = [line.group().strip() for line in lines]
        index = 0
        while index < len(lines):
            text = texts[index]
            if text.casefold() == "item":
                end = index + 1
                while end < len(lines):
                    if SUMMARY.fullmatch(texts[end]) or VAT_LABEL.match(texts[end]) or SECTION.match(texts[end]):
                        break
                    end += 1
                excerpt = Evidence(page.page_number, page.text[lines[index].start():lines[end - 1].end()])
                values = _read_table(texts[index:end])
                if values is None:
                    for name in ITEM_FIELDS + ("unit_price_tax_note",):
                        unsupported[name].append(excerpt)
                else:
                    # Preserve the description's original whitespace in its value.
                    header_length = 6 if texts[index + 5].casefold() == "amount (bdt)" else 5
                    first = index + header_length + 1
                    values["description"] = page.text[lines[first].start():lines[end - 5].end()].strip()
                    for name, value in values.items():
                        candidates[name].append((value, excerpt))
                index = end  # Consume the table; its descriptions cannot become totals.
                continue

            summary = SUMMARY.fullmatch(text)
            vat_label = VAT_LABEL.match(text)
            if summary or vat_label:
                name = "subtotal" if summary and summary.group("label").casefold() == "subtotal" else "total"
                value = (summary.group("colon") or summary.group("inline") or "") if summary else ""
                if vat_label:
                    name = "vat_amount"
                    vat = re.fullmatch(rf"VAT\s+(?P<rate>{NUMBER})\s*%\s*:?[ \t]*(?P<amount>.*)", text, re.I)
                    if vat is None:
                        excerpt = Evidence(page.page_number, lines[index].group())
                        unsupported["vat_rate"].append(excerpt)
                        unsupported["vat_amount"].append(excerpt)
                        index += 1
                        continue
                    candidates["vat_rate"].append((vat.group("rate"), Evidence(page.page_number, lines[index].group())))
                    value = vat.group("amount")
                last = index
                if not value and index + 1 < len(lines):
                    last = index + 1
                    value = texts[last]
                excerpt = Evidence(page.page_number, page.text[lines[index].start():lines[last].end()])
                if re.fullmatch(NUMBER, value):
                    candidates[name].append((value, excerpt))
                else:
                    unsupported[name].append(excerpt)
            index += 1
    return {name: resolve_field(candidates[name], unsupported[name]) for name in FIELD_NAMES}


def main() -> int:
    return preview(extract_financial_details, REQUIRED_FIELDS)


if __name__ == "__main__":
    raise SystemExit(main())
