"""Read the numbered contract terms used by the supplied quotation template."""

import re

from procurement.extraction import Evidence, preview, resolve_field
from procurement.pdf_text import PdfDocument

FIELD_NAMES = ("advance_percent", "payment_days", "delivery_days", "penalty_clause",
               "penalty_percent", "penalty_basis", "validity_days")
CLAUSES = re.compile(
    r"^\d+\.[ \t]+(?P<label>Payment|Delivery|Delay|Validity)\.[ \t]*(?P<body>.*?)"
    r"(?=^\d+\.[ \t]+\w+\.|^For[ \t]+|\Z)", re.I | re.M | re.S,
)


def _read_term(name: str, text: str) -> list[str]:
    """Return supported values in one clause; an empty list means uncertainty."""
    text = " ".join(text.split())
    # Conditional or negative wording changes the meaning of a numeric promise.
    if re.search(r"\b(if|unless|subject to|may|not|excluding|up to)\b", text, re.I):
        return []
    if name == "advance_percent":
        if re.search(r"\bNo advance payment required\b", text, re.I):
            return ["0"]
        return re.findall(r"([0-9]+(?:\.[0-9]+)?)%\s+advance\b", text, re.I)
    if name == "payment_days":
        return re.findall(r"\bwithin ([0-9]+) days (?:after|of) delivery\b", text, re.I)
    if name == "delivery_days":
        matches = re.findall(
            r"\bwithin ([0-9]+) (days|weeks) (?:of|from) "
            r"(?:receiving |the date of )?(?:the )?(?:purchase order|PO)\b", text, re.I,
        )
        return [str(int(value) * (7 if unit.lower() == "weeks" else 1)) for value, unit in matches]
    if name == "validity_days":
        return re.findall(r"\bvalid for ([0-9]+) days from the date above\b", text, re.I)
    if name == "penalty_clause":
        if re.search(r"\bNo late delivery penalty\b", text, re.I):
            return ["absent"]
        if re.search(r"\b(?:late delivery|delay in delivery)\b", text, re.I) and "%" in text:
            return ["present"]
    if name == "penalty_percent":
        return re.findall(r"([0-9]+(?:\.[0-9]+)?)%", text)
    if name == "penalty_basis":
        if re.search(r"% of (?:the )?order value (?:per week|for each full week of delay)\b", text, re.I):
            return ["order_value_per_week"]
    return []


def extract_terms(document: PdfDocument) -> dict:
    """Read payment, delivery, penalty, and validity; retain unresolved wording."""
    candidates = {name: [] for name in FIELD_NAMES}
    unsupported = {name: [] for name in FIELD_NAMES}
    fields_by_clause = {"payment": ("advance_percent", "payment_days"),
                        "delivery": ("delivery_days",), "validity": ("validity_days",),
                        "delay": ("penalty_clause", "penalty_percent", "penalty_basis")}
    for page in document.pages:
        for clause in CLAUSES.finditer(page.text):
            excerpt = Evidence(page.page_number, clause.group().rstrip())
            for name in fields_by_clause[clause.group("label").lower()]:
                values = _read_term(name, clause.group("body"))
                if values:
                    for value in values:
                        candidates[name].append((value, excerpt))
                else:
                    unsupported[name].append(excerpt)
    return {name: resolve_field(candidates[name], unsupported[name]) for name in FIELD_NAMES}


def main() -> int:
    return preview(extract_terms, FIELD_NAMES)


if __name__ == "__main__":
    raise SystemExit(main())
