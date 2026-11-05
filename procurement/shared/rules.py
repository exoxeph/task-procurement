"""Company checks and the final decision, kept together in reading order."""

import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from procurement.shared.extraction import (
    Evidence, ExtractedField, ExtractionRun, NUMERIC_FIELDS,
    explicit_penalty_absence, read_number, validate_fields,
)
from procurement.shared.pdf_text import PdfDocument

REVIEW = "Needs a person to check"
REJECT = "Reject"


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    reason: str
    evidence: tuple[Evidence, ...]
    field_names: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReviewResult:
    document: PdfDocument
    fields: dict[str, ExtractedField]
    findings: tuple[Finding, ...]
    verdict: str
    extraction_run: ExtractionRun | None = None
    steps: tuple = ()


def check_rules(document: PdfDocument, fields: dict, items: dict, policy: dict) -> ReviewResult:
    """Convert values, check each rule, retain findings, then choose the verdict."""
    thresholds = policy["thresholds"]
    requirements = policy["requirements"]
    validation = validate_fields(fields, document)
    fields = validation.fields
    findings = []
    inspected_pages = tuple(Evidence(page.page_number, page.text) for page in document.pages)

    def add(code, severity, reason, *field_names):
        excerpts = []
        for name in field_names:
            excerpts.extend(fields[name].evidence)
        # Absence has no fabricated quote: cite the actual pages inspected.
        evidence = tuple(dict.fromkeys(excerpts)) or inspected_pages
        findings.append(Finding(code, severity, reason, evidence, tuple(field_names)))

    # 1. Extraction uncertainty must never silently turn into approval.
    for issue in document.issues:
        add("pdf_issue", REVIEW, issue)
    for issue in validation.issues:
        add("extraction_issue", REVIEW, issue)
    required = ("supplier_name", "quotation_number", "quotation_date", "purchase_request_reference",
                "item_code", "description", "quantity", "unit", "unit_price", "line_amount", "total",
                "advance_percent", "payment_days", "delivery_days", "validity_days")
    for name in required:
        if fields[name].status != "found":
            code = "payment" if name == "payment_days" else f"extraction_{name}"
            add(code, REVIEW, f"Cannot confidently read {name}: {fields[name].status}.", name)
    for name, field in fields.items():
        # VAT figures, registrations and penalty fields have dedicated checks
        # below. The optional price note also needs an uncertainty check.
        if name == "unit_price_tax_note" and field.status in ("ambiguous", "unrecognized"):
            add(f"extraction_{name}", REVIEW, f"Cannot confidently read {name}: {field.status}.", name)
        if (name.endswith("_clause_text") or name.endswith("_reference")) and field.status in ("ambiguous", "unrecognized"):
            add(f"extraction_{name}", REVIEW, f"Conflicting or unsupported source interpretation for {name}.", name)
        if field.status == "found" and requirements["exact_evidence"] and not field.evidence:
            add("missing_evidence", REVIEW, f"No supporting excerpt for {name}.")

    # 2. Convert text locally. The extractor still retains the original strings.
    numbers = {}
    for name in NUMERIC_FIELDS:
        field = fields[name]
        if field.status == "found":
            # Shared validation has already checked the format and bounds.
            numbers[name] = read_number(field.value, name)

    # A duration must have the right starting event. Unresolved qualifications
    # cannot be dropped merely because its numeric value looks compliant.
    expected_events = {"payment_days": "delivery", "delivery_days": "purchase_order",
                       "validity_days": "quotation_date"}
    qualified_fields = set()
    for name, fact in fields.items():
        if fact.status != "found":
            continue
        wrong_event = name in expected_events and fact.reference_event != expected_events[name]
        has_range = (fact.minimum_value is not None and fact.maximum_value is not None
                     and Decimal(fact.minimum_value.replace(',', '')) != Decimal(fact.maximum_value.replace(',', '')))
        if wrong_event or fact.conditions or has_range:
            qualified_fields.add(name)
            add("payment" if name == "payment_days" else f"qualified_{name}", REVIEW,
                f"Cannot apply {name} without resolving its reference event, conditions or range.", name)
            numbers.pop(name, None)

    currency = fields["currency"]
    currency_supported = currency.status == "found" and currency.value == "BDT" and not currency.conditions
    if not currency_supported:
        add("currency", REVIEW, "Cannot compare monetary figures without an explicit supported BDT currency.", "currency")
        for name in ("unit_price", "line_amount", "subtotal", "vat_amount", "total"):
            numbers.pop(name, None)

    # 3. Match the request before comparing quantities or prices.
    item = items.get(fields["item_code"].value)
    if item is None:
        add("request_item", REVIEW, "Item could not be matched to the purchase request.", "item_code")
    else:
        if fields["purchase_request_reference"].value != item.pr_number:
            add("request_reference", REVIEW, f"Expected purchase request {item.pr_number}.", "purchase_request_reference")
        if fields["unit"].value is None or fields["unit"].value.casefold() != item.unit.casefold():
            add("request_unit", REVIEW, f"Requested unit is {item.unit}.", "unit")
        description = " ".join((fields["description"].value or "").split()).casefold()
        if description != " ".join(item.description.split()).casefold():
            add("request_description", REVIEW, f"Requested item is {item.description}.", "description")
        price = numbers.get("unit_price")
        if price is not None and price > item.maximum_unit_price:
            limit = item.maximum_unit_price * (1 + thresholds["price_review_tolerance_percent"] / 100)
            severity = REJECT if price > limit else REVIEW
            add("price", severity, f"Quoted BDT {price}; maximum BDT {item.maximum_unit_price}; rejection above BDT {limit}.", "unit_price")
        quantity = numbers.get("quantity")
        if quantity is not None:
            difference = abs(quantity - item.quantity_requested) / item.quantity_requested * 100
            if difference > thresholds["quantity_review_tolerance_percent"]:
                add("quantity", REVIEW, f"Quantity differs by {difference:.2f}% from requested {item.quantity_requested}.", "quantity")

    # 4. Registration absence is different from an unknown extraction format.
    text = "\n".join(page.text for page in document.pages)
    for name in ("tin", "bin"):
        if requirements[name] and fields[name].status != "found":
            confirmed = re.search(rf"\b{name}\s*:\s*(?:missing|none|not provided|not available)(?:[.;]|$)",text,re.I | re.M) is not None
            add("registration_missing" if confirmed else "registration_unclear", REJECT if confirmed else REVIEW,
                f"{name.upper()} is explicitly marked as not supplied." if confirmed
                else f"Cannot establish {name.upper()} from this document.", name)

    # 5. Payment, delivery, and quotation validity thresholds.
    if numbers.get("advance_percent", 0) > thresholds["maximum_advance_percent"]:
        add("advance", REJECT, f"Advance exceeds {thresholds['maximum_advance_percent']}%.", "advance_percent")
    payment = numbers.get("payment_days")
    if payment is not None and not thresholds["minimum_payment_days"] <= payment <= thresholds["maximum_payment_days"]:
        add("payment", REVIEW, f"Payment is {payment} days after delivery, outside the allowed window.", "payment_days")
    delivery = numbers.get("delivery_days")
    if delivery is not None:
        if delivery > thresholds["maximum_delivery_days"]:
            add("delivery", REJECT, f"Delivery in {delivery} days exceeds {thresholds['maximum_delivery_days']} days after PO.", "delivery_days")
        elif delivery > thresholds["maximum_automatic_delivery_days"]:
            add("delivery", REVIEW, f"Delivery in {delivery} days needs review.", "delivery_days")
    validity = numbers.get("validity_days")
    if validity is not None and validity < thresholds["minimum_quotation_validity_days"]:
        add("validity", REVIEW, f"Quotation valid for only {validity} days.", "validity_days")

    # 6. Penalty: reject confirmed absence, review an unclear or weak clause.
    if requirements["late_delivery_penalty"]:
        clause = fields["penalty_clause"]
        absent = (clause.status == "found" and clause.value == "absent"
                  and "penalty_clause" not in qualified_fields and explicit_penalty_absence(clause.evidence))
        if absent:
            add("penalty_missing", REJECT, "Document explicitly states no late-delivery penalty.", "penalty_clause")
        elif clause.value != "present":
            add("penalty_unclear", REVIEW, "Could not establish a late-delivery penalty clause.", "penalty_clause")
        else:
            rate = numbers.get("penalty_percent")
            if rate is None or rate < thresholds["minimum_weekly_penalty_percent"]:
                add("penalty_rate", REVIEW, "Penalty rate is unclear or below the weekly minimum; severity is unspecified in policy.", "penalty_percent")
            if fields["penalty_basis"].value != "order_value_per_week":
                add("penalty_basis", REVIEW, "Cannot establish a weekly penalty based on order value.", "penalty_basis")

    # 7. VAT display and arithmetic; never fill in an unstated amount.
    if requirements["separate_vat"] and (numbers.get("vat_rate") != thresholds["required_vat_percent"]
                                         or "vat_amount" not in numbers or "subtotal" not in numbers
                                         or (fields["unit_price_tax_note"].value or "").lower() == "vat included"):
        add("vat_display", REVIEW, "VAT must be shown separately at the required rate.", "vat_rate", "vat_amount", "unit_price_tax_note")
    if requirements["correct_totals"]:
        calculations = (
            ("line_arithmetic", ("quantity", "unit_price", "line_amount"), lambda: numbers["quantity"] * numbers["unit_price"]),
            ("subtotal_arithmetic", ("line_amount", "subtotal"), lambda: numbers["line_amount"]),
            ("vat_arithmetic", ("subtotal", "vat_rate", "vat_amount"), lambda: numbers["subtotal"] * numbers["vat_rate"] / 100),
            ("total_arithmetic", ("subtotal", "vat_amount", "total"), lambda: numbers["subtotal"] + numbers["vat_amount"]),
        )
        for code, names, calculate in calculations:
            if all(name in numbers for name in names):
                expected = calculate().quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                if expected != numbers[names[-1]]:
                    add(code, REVIEW, f"Expected {names[-1]} BDT {expected}; document states BDT {numbers[names[-1]]}.", *names)

    # 8. One priority rule, preserving every finding even after rejection.
    severities = {finding.severity for finding in findings}
    verdict = next((severity for severity in policy["decision_priority"] if severity in severities), "Approve")
    return ReviewResult(document, fields, tuple(findings), verdict)
