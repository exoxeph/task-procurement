"""Small records shared by the baseline's document extraction steps."""

from dataclasses import dataclass


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
