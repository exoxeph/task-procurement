"""Read item cells by table geometry and column meaning, then labelled totals."""

import re

from procurement.shared.extraction import Evidence, ExtractedField, preview, resolve_field
from procurement.shared.pdf_text import PdfDocument


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
# This small vocabulary describes column concepts, not whole supplier templates.
COLUMN_NAMES = {
    "item_code": {"item", "item code", "sku", "code"},
    "description": {"description", "product", "item description"},
    "quantity": {"qty", "quantity"},
    "unit": {"unit", "uom"},
    "unit_price": {"unit price", "price per unit"},
    "line_amount": {"amount", "line total", "line amount"},
}


def _read_table(table) -> dict | None:
    """Map labelled columns, whatever their order; reject an uncertain mapping."""
    columns = {}
    for index, header in enumerate(table.headers):
        label = re.sub(r"\([^)]*\)", "", header).strip().casefold()
        label = " ".join(label.split())
        for name, aliases in COLUMN_NAMES.items():
            if label in aliases:
                if name in columns:
                    return None
                columns[name] = index
    if set(columns) != set(ITEM_FIELDS) or len(table.rows) != 1:
        return None  # Multiple rows need a future item-list schema, not selection.
    for name in ("unit_price", "line_amount"):
        header = table.headers[columns[name]]
        if re.search(r"\b(?:USD|EUR|GBP|INR|CNY)\b|[$\u20ac\u00a3]", header, re.I):
            return None
        if not re.search(r"\bBDT\b|\u09f3", header, re.I):
            return None  # Currency must be explicit; do not assume BDT.
        # Extra price bases such as 'BDT per kg' cannot be discarded as decoration.
        qualifier = re.sub(r"^[^(]*",'',header)
        qualifier = re.sub(r"\bBDT\b|\u09f3|VAT\s+(?:included|excluded)",'',qualifier,flags=re.I)
        if re.sub(r"[\s(),]",'',qualifier):
            return None
    values = {name: table.rows[0][index].strip() for name,index in columns.items()}
    if not all(values.values()) or not any(letter.isalpha() for letter in values['description']):
        return None
    for name in ("quantity", "unit_price", "line_amount"):
        if not re.fullmatch(INTEGER if name == "quantity" else NUMBER, values[name]):
            return None
    note = re.search(r"VAT\s+(?:included|excluded)", table.headers[columns['unit_price']], re.I)
    if note:
        values['unit_price_tax_note'] = note.group()
    return values


def extract_financial_details(document: PdfDocument) -> dict[str, ExtractedField]:
    """Read structural item cells and explicit totals, keeping original page evidence."""
    candidates = {name: [] for name in FIELD_NAMES}
    unsupported = {name: [] for name in FIELD_NAMES}
    for page in document.pages:
        # A page excerpt remains exact even when cells were inserted out of order.
        excerpt = Evidence(page.page_number, page.text)
        for table in page.tables:
            values = _read_table(table)
            if values is None:
                for name in ITEM_FIELDS + ("unit_price_tax_note",):
                    unsupported[name].append(excerpt)
            else:
                for name,value in values.items():
                    candidates[name].append((value,excerpt))
        text = page.outside_tables_text if page.outside_tables_text is not None else page.text
        # Detect an apparent item table that geometry could not consume. Do not
        # extract its row from text order or let a different valid table hide it.
        concepts = set()
        for name,aliases in COLUMN_NAMES.items():
            if any(re.search(r"\b"+re.escape(alias).replace(r"\ ",r"\s+")+r"\b",text,re.I) for alias in aliases):
                concepts.add(name)
        if 'quantity' in concepts and 'unit_price' in concepts and len(concepts) >= 3:
            for name in ITEM_FIELDS:
                unsupported[name].append(excerpt)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for index,line in enumerate(lines):
            summary = SUMMARY.fullmatch(line)
            vat_label = VAT_LABEL.match(line)
            if not summary and not vat_label:
                continue
            name = "subtotal" if summary and summary.group('label').casefold() == 'subtotal' else 'total'
            if summary:
                qualifier = re.search(r"\(([^)]*)\)",summary.group('label'))
                if qualifier and not set(re.findall(r"\w+",qualifier.group(1).casefold())) <= {'bdt','all','taxes','vat','included','excluded'}:
                    unsupported[name].append(excerpt)
                    continue
            value = (summary.group('colon') or summary.group('inline') or '') if summary else ''
            if vat_label:
                name = 'vat_amount'
                vat = re.fullmatch(rf"VAT\s+(?P<rate>{NUMBER})\s*%\s*:?[ \t]*(?P<amount>.*)",line,re.I)
                if vat is None:
                    unsupported['vat_rate'].append(excerpt)
                    unsupported['vat_amount'].append(excerpt)
                    continue
                candidates['vat_rate'].append((vat.group('rate'),excerpt))
                value = vat.group('amount')
            if not value and index+1 < len(lines):
                value = lines[index+1]
            if re.fullmatch(NUMBER,value):
                candidates[name].append((value,excerpt))
            else:
                unsupported[name].append(excerpt)
    return {name: resolve_field(candidates[name],unsupported[name]) for name in FIELD_NAMES}


def main() -> int:
    return preview(extract_financial_details,REQUIRED_FIELDS)


if __name__ == "__main__":
    raise SystemExit(main())
