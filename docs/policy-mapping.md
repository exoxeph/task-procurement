# How the company rules map to code

The source of truth is
`sample-data/engineer/task1-procurement/company-rules.md`.
`config/company-rules.json` is its manually reviewed machine-readable companion.
references.py loads and validates that companion. rules.py implements the
comparisons and decisions below; the loader does not enforce supplier policy.

Percent settings use percentage points: `3.0` means 3%, not 0.03. For example,
the price difference can be expressed as `(quoted - maximum) / maximum * 100`.

| Source rule | Setting or future check | Outcome |
| --- | --- | --- |
| Price more than 3% above maximum | `price_review_tolerance_percent: 3.0` | Reject |
| Advance more than 20% | `maximum_advance_percent: 20.0` | Reject |
| No late-delivery penalty clause | `requirements.late_delivery_penalty: true` | Reject |
| TIN or BIN missing | `requirements.tin` and `requirements.bin` | Reject |
| Delivery later than 45 days after PO | `maximum_delivery_days: 45` | Reject |
| Price above maximum, up to 3% above | Same price tolerance; exactly 3% belongs here | Human review |
| Quantity differs by more than 5% | `quantity_review_tolerance_percent: 5.0`; absolute difference | Human review |
| Payment unclear or outside 30-60 days after delivery | `minimum_payment_days: 30`, `maximum_payment_days: 60`; ambiguity is also checked | Human review |
| Delivery in 31-45 days | `maximum_automatic_delivery_days: 30`, `maximum_delivery_days: 45` | Human review |
| VAT not separately shown at 15% | `requirements.separate_vat`, `required_vat_percent: 15.0` | Human review |
| Numbers do not add up | `requirements.correct_totals`; recalculate line, subtotal, VAT, and total | Human review |
| Validity less than 30 days | `minimum_quotation_validity_days: 30` | Human review |
| None of the above | No failures and no unresolved relevant facts | Approve |
| Weekly penalty must be at least 0.5% of order value | `minimum_weekly_penalty_percent: 0.5`; verify basis and frequency too | See ambiguity below |
| Always quote exact supporting text | `requirements.exact_evidence` | Preserve document evidence |
| If uncertain, never guess | `on_uncertainty: Needs a person to check` | Human review |

The source says review conditions apply only if no reject condition applies.
`decision_priority` records Reject > Needs a person to check > Approve. All
findings will still be retained, even when one determines the final verdict.

## Important distinctions

- Exactly 20% advance does not trigger the advance rejection rule.
- Exactly 5% quantity difference does not trigger the quantity review rule.
- Payment at 30 or 60 days is within the stated payment window.
- Delivery at 45 days requires review; delivery above 45 days is rejected.
- A confirmed missing registration field differs from unreadable text that a
  parser could not interpret. Extraction uncertainty requires human review.
- A missing clause has no supporting quotation to invent. Record the missing
  clause and the inspected document/page; preserve other available evidence.

## Ambiguous severity of a weak penalty

The source requires a penalty of at least 0.5% per week but explicitly lists
only a *missing* penalty clause as a rejection. It does not assign a severity
to an existing clause with a lower penalty. Our documented interpretation for
rules.py is human review under the source's uncertainty instruction. Do not
silently turn that into an automatic rejection.

## Keeping the files in sync

No AI or general Markdown parser interprets the policy. When the source policy
changes, review this mapping and update the JSON. Block 1 validates input
structure and values; it does not automatically detect semantic differences
between the Markdown and JSON.
