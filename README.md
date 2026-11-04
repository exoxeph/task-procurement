# Procurement reviewer: simple Python baseline

Read PDF -> extract facts -> check rules and decide -> show evidence.

This baseline uses deterministic Python parsing. It is the comparison baseline
for a later AI extractor, not yet the AI system requested by the interview brief.
All ten samples are visible during development; results are not an unseen benchmark.

## Run extraction

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -q
python -m procurement.financial_details sample-data/engineer/task1-procurement/supplier-pack-09.pdf
python -m procurement.terms sample-data/engineer/task1-procurement/supplier-pack-01.pdf
```

## Read the code in this order

| File | Responsibility |
| --- | --- |
| `procurement/pdf_text.py` | Read PDF text with page numbers and file issues |
| `procurement/supplier_details.py` | Supplier, quote, request reference, TIN and BIN |
| `procurement/financial_details.py` | Read a table, then labelled totals |
| `procurement/terms.py` | Payment, delivery, penalty and validity |
| `procurement/extraction.py` | Shared field records, status resolution and preview |
| `procurement/references.py` | Load purchase request and policy settings |

Start with `extract_financial_details()`: it walks page lines, consumes a table
when it reaches Item, then reads totals. `_read_table()` assigns the row values.
There is no separate line class, totals collector, or table-line tracking set.

Each field has a value, status, and exact page evidence. `found` means the value
was read, not that it passes policy. Conflicting or unsupported values remain
unresolved. Original PDF reading issues must stay alongside extracted fields.
Pack 09 preserves its incorrect stated amount. Pack 10 has no invented VAT rows.

## Supported format

Selectable PDF text in native reading order; one item per table; BDT prices;
known column labels; numbered Payment, Delivery, Delay, Validity clauses.
Descriptions can wrap. Unknown formats and conditions need human review.
No OCR, arbitrary table-layout support, or legal registration validation.

The supplied company-rules.md is authoritative. config/company-rules.json is a
manual transcription; docs/policy-mapping.md explains boundaries and ambiguities.
Source sample files are unchanged. The unrelated video/ folder is not part of this work.

The current design is docs/superpowers/specs/2026-11-05-simple-baseline-design.md.
The old ten-block documents are historical; the three-stage plan supersedes them.
