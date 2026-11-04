# Sample results

All ten supplied documents were visible during development. These are development
results, not an unseen benchmark. Expected labels were manually reviewed. Duplicate
findings such as missing TIN and BIN are compared as one triggered rule code.

| Document | Expected | Actual | Rule sets match | Reason |
| --- | --- | --- | --- | --- |
| supplier-pack-01.pdf | Approve | Approve | Yes | All supplied requirements pass. |
| supplier-pack-02.pdf | Approve | Approve | Yes | No advance, 30-day payment, 21-day delivery, acceptable figures and penalty. |
| supplier-pack-03.pdf | Reject | Reject | Yes | 229 exceeds the thread maximum 210 by more than 3%. |
| supplier-pack-04.pdf | Needs a person to check | Needs a person to check | Yes | 6.65 exceeds 6.50 by about 2.31%. |
| supplier-pack-05.pdf | Reject | Reject | Yes | 40% advance exceeds 20%. |
| supplier-pack-06.pdf | Reject | Reject | Yes | Recognized complete terms omit the late-delivery penalty. |
| supplier-pack-07.pdf | Needs a person to check | Needs a person to check | Yes | 16,500 zippers versus 20,000 requested: 17.5% difference. |
| supplier-pack-08.pdf | Reject | Reject | Yes | TIN/BIN withheld as available on request; penalty does not state the order-value basis. |
| supplier-pack-09.pdf | Needs a person to check | Needs a person to check | Yes | 30-to-90-day payment as agreed lacks a clear delivery anchor; 50,000 x 6.40 is 320,000, not 322,000. |
| supplier-pack-10.pdf | Reject | Reject | Yes | 60-day delivery exceeds 45; VAT-inclusive total has no separate VAT breakdown. |

Verdict matches: 10/10. Triggered-rule set matches: 10/10.

Reproduce with `python -m procurement.review`. Exact field checks and regression
tests run with `python -m unittest discover -s tests -q`.

Pack 08 also needs review of its unstated penalty basis, while missing registration
determines the rejection. Pack 10 has a VAT review finding, while delivery determines
the rejection. These secondary findings remain visible in the report.
