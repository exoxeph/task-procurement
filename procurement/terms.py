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
PERCENT = r"[0-9]+(?:\.[0-9]+)?"
PENALTY = re.compile(
    rf"(?:Late delivery penalty(?::| of)|For late delivery the supplier shall pay|"
    rf"Delay in delivery will attract a penalty of) (?P<rate>{PERCENT})%"
    r"(?P<basis> of (?:the )?order value)? "
    r"(?:per week(?: of delay)?|for each full week of delay)\.?", re.I,
)


def _read_term(name: str, text: str) -> list[str]:
    """Return supported values in one clause; an empty list means uncertainty."""
    text = " ".join(text.split())
    # Validate complete percentage tokens, never a positive suffix of '-0.5%'.
    if any(not re.fullmatch(PERCENT, token) for token in re.findall(r"(\S+)%", text)):
        return []
    if re.search(r"\b(if|unless|subject to|may|not|excluding|up to)\b", text, re.I):
        return []
    if name == "advance_percent":
        values = re.findall(rf"({PERCENT})%\s+advance\b", text, re.I)
        if re.search(r"\bNo advance payment required\b", text, re.I):
            values.append("0")
        return values  # A zero statement and a positive advance remain conflicting.
    if name == "payment_days":
        # Remove supported advance sentences, then require the entire balance
        # statement to match. Additional qualifications cannot be ignored.
        payment = re.sub(rf"(?:No advance payment required|{PERCENT}% advance payable with the purchase order)\.\s*", "", text, flags=re.I)
        combined = re.fullmatch(rf"{PERCENT}% advance with the purchase order, balance {PERCENT}% (?P<rest>within .*)", payment, re.I)
        if combined:
            payment = "Balance " + combined.group("rest")
        match = re.fullmatch(r"(?:Payment|Full payment|Balance(?: payable)?) within (?P<days>[0-9]+) days (?:after|of) delivery(?: and acceptance of goods)?\.?", payment, re.I)
        return [match.group("days")] if match else []
    if name == "delivery_days":
        match = re.fullmatch(
            r"(?:Delivery|Goods will be delivered at your factory) within (?P<value>[0-9]+) (?P<unit>days|weeks) (?:of|from) "
            r"(?:receiving |the date of )?(?:the )?(?:purchase order|PO)\.?", text, re.I,
        )
        if match:
            return [str(int(match.group("value")) * (7 if match.group("unit").lower() == "weeks" else 1))]
        return []
    if name == "validity_days":
        match = re.fullmatch(r"This quotation is valid for (?P<days>[0-9]+) days from the date above\.?", text, re.I)
        return [match.group("days")] if match else []
    if name == "penalty_clause" and re.fullmatch(r"No late delivery penalty applies\.?", text, re.I):
        return ["absent"]
    penalty = PENALTY.fullmatch(text)
    if penalty:
        if name == "penalty_clause":
            return ["present"]
        if name == "penalty_percent":
            return [penalty.group("rate")]
        if name == "penalty_basis" and penalty.group("basis"):
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
