"""Block 1: load purchase requirements and company policy, not supplier PDFs."""

import csv
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path


# Resolve defaults from this file, so changing the terminal directory is safe.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DIRECTORY = PROJECT_ROOT / "sample-data/engineer/task1-procurement"
DEFAULT_PURCHASE_REQUEST = SAMPLE_DIRECTORY / "purchase-request.csv"
DEFAULT_COMPANY_RULES = PROJECT_ROOT / "config/company-rules.json"

CSV_COLUMNS = (
    "PR number", "Item", "Description", "Unit", "Quantity requested",
    "Maximum unit price (BDT)",
)

THRESHOLD_NAMES = (
    "price_review_tolerance_percent",
    "maximum_advance_percent",
    "quantity_review_tolerance_percent",
    "minimum_payment_days",
    "maximum_payment_days",
    "maximum_automatic_delivery_days",
    "maximum_delivery_days",
    "required_vat_percent",
    "minimum_quotation_validity_days",
    "minimum_weekly_penalty_percent",
)

REQUIREMENT_NAMES = (
    "late_delivery_penalty", "tin", "bin", "separate_vat", "correct_totals",
    "exact_evidence",
)


@dataclass(frozen=True)
class PurchaseRequestItem:
    """One requested item. Frozen prevents accidental changes after loading."""

    pr_number: str
    item_code: str
    description: str
    unit: str
    quantity_requested: int
    maximum_unit_price: Decimal


def load_purchase_request(
    path: Path = DEFAULT_PURCHASE_REQUEST,
) -> dict[str, PurchaseRequestItem]:
    """Return requested items keyed by code, such as items['A']."""
    items = {}

    # utf-8-sig handles UTF-8 files both with and without a byte-order mark.
    with Path(path).open(encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        missing_columns = set(CSV_COLUMNS) - set(reader.fieldnames or [])
        if missing_columns:
            raise ValueError(f"Missing CSV columns: {', '.join(sorted(missing_columns))}")

        for row_number, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(f"CSV row {row_number}: too many values.")

            for column in CSV_COLUMNS:
                if not row.get(column) or not row[column].strip():
                    raise ValueError(f"CSV row {row_number}: missing {column}.")
                row[column] = row[column].strip()

            item_code = row["Item"]
            if item_code in items:
                raise ValueError(f"Duplicate item {item_code!r} at CSV row {row_number}.")

            try:
                quantity = int(row["Quantity requested"])
            except ValueError:
                raise ValueError(f"CSV row {row_number}: quantity must be a positive integer.") from None
            if quantity <= 0:
                raise ValueError(f"CSV row {row_number}: quantity must be a positive integer.")

            try:
                price = Decimal(row["Maximum unit price (BDT)"])
            except InvalidOperation:
                raise ValueError(f"CSV row {row_number}: invalid maximum unit price.") from None
            if not price.is_finite() or price < 0:
                raise ValueError(f"CSV row {row_number}: unit price must be finite and non-negative.")

            items[item_code] = PurchaseRequestItem(
                pr_number=row["PR number"],
                item_code=item_code,
                description=row["Description"],
                unit=row["Unit"],
                quantity_requested=quantity,
                maximum_unit_price=price,
            )

    if not items:
        raise ValueError("No purchase request items found in the CSV.")
    return items


def load_company_rules(path: Path = DEFAULT_COMPANY_RULES) -> dict:
    """Load the reviewed JSON transcription; do not interpret Markdown."""
    try:
        with Path(path).open(encoding="utf-8") as policy_file:
            rules = json.load(policy_file, parse_float=Decimal)
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid policy JSON: {error.msg}.") from error

    if not isinstance(rules, dict):
        raise ValueError("Company rules must be a JSON object.")

    thresholds = rules.get("thresholds")
    if not isinstance(thresholds, dict):
        raise ValueError("Policy must contain a thresholds object.")

    for name in THRESHOLD_NAMES:
        value = thresholds.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
            raise ValueError(f"Policy threshold {name} must be a non-negative number.")
        if not Decimal(value).is_finite() or value < 0:
            raise ValueError(f"Policy threshold {name} must be finite and non-negative.")
        if name.endswith("_days") and value != int(value):
            raise ValueError(f"Policy threshold {name} must be a whole number of days.")

    if thresholds["minimum_payment_days"] > thresholds["maximum_payment_days"]:
        raise ValueError("Policy minimum payment days cannot exceed maximum payment days.")
    if thresholds["maximum_automatic_delivery_days"] > thresholds["maximum_delivery_days"]:
        raise ValueError("Policy automatic delivery limit cannot exceed maximum delivery days.")

    requirements = rules.get("requirements")
    if not isinstance(requirements, dict):
        raise ValueError("Policy must contain a requirements object.")
    for name in REQUIREMENT_NAMES:
        if not isinstance(requirements.get(name), bool):
            raise ValueError(f"Policy requirement {name} must be true or false.")

    expected_priority = ["Reject", "Needs a person to check", "Approve"]
    if rules.get("decision_priority") != expected_priority:
        raise ValueError("Policy decision_priority must be Reject, human review, then Approve.")
    if rules.get("on_uncertainty") != "Needs a person to check":
        raise ValueError("Policy on_uncertainty must be Needs a person to check.")

    return rules


def main() -> None:
    """Print reference inputs so Block 1 can be tried without other blocks."""
    try:
        items = load_purchase_request()
        rules = load_company_rules()
    except (OSError, ValueError) as error:
        raise SystemExit(f"Cannot load reference data: {error}") from error

    print(f"Loaded {len(items)} purchase request items:\n")
    for item in items.values():
        print(f"{item.item_code}: {item.description}")
        print(f"  Requested: {item.quantity_requested:,} {item.unit}")
        print(f"  Maximum unit price: BDT {item.maximum_unit_price:.2f}")

    print("\nLoaded company policy thresholds:")
    for name, value in rules["thresholds"].items():
        print(f"  {name}: {value}")
    print("\nDecision priority: " + " > ".join(rules["decision_priority"]))
    print("\nBlock 1 loads reference inputs. Supplier checks come in later blocks.")


if __name__ == "__main__":
    main()
