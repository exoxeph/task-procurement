"""Experiment: a second AI pass that checks extracted facts against the source.

Advisory only. It can flag a fact for a person; it never approves anything and never
overrides a failed code check. Reads a saved run, makes one call, prints per-fact verdicts.

    python -m procurement.verifier <saved-run.json> [--model qwen/qwen3-14b]
"""

import argparse
import json
import os
from pathlib import Path
import sys

from procurement.approach2.openrouter import urlopen, URL, provider_preferences, sampling_options
from procurement.shared.env import load_env
from procurement.shared.extraction import locate_excerpt, parse_json
from procurement.shared.pdf_text import read_pdf
from procurement.shared.runs import read_run
from urllib.request import Request

# The terms where a dropped qualifier changes the business meaning.
CHECKED_FACTS = ("advance_percent", "payment_days", "delivery_days", "validity_days",
                 "penalty_clause", "penalty_percent", "penalty_basis")
VERDICTS = ("supported", "qualifier_missing", "unsupported")
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["checks"], "properties": {"checks": {
    "type": "array", "items": {"type": "object", "additionalProperties": False,
                               "required": ["fact", "verdict", "missing_text", "reason"],
                               "properties": {"fact": {"type": "string", "enum": list(CHECKED_FACTS)},
                                              "verdict": {"type": "string", "enum": list(VERDICTS)},
                                              "missing_text": {"type": ["string", "null"]},
                                              "reason": {"type": "string"}}}}}}
PROMPT = """You audit extracted facts from a supplier quotation against its source text.
For each fact given, decide whether the extracted value, event and conditions fully and
exactly capture what the document says in the matching clause. Read the WHOLE clause.

Verdicts:
- supported: the value, reference_event and conditions together capture the clause; nothing
  that changes the meaning is left out.
- qualifier_missing: the clause contains a qualifier, condition, exception, approval,
  acceptance step, scope limit or alternative that the fact leaves out (conditions is empty
  or incomplete), so the plain value overstates what the document promises.
- unsupported: the value or event contradicts the clause or is not in the document.

For qualifier_missing, missing_text must be the qualifier copied exactly from the source
text; otherwise null. Do not flag wording that is merely different but means the same.
Do not suggest approving or rejecting anything. Return one check per fact given, no others.
"""


def fact_payload(fields):
    """The extracted facts exactly as the extractor produced them."""
    payload = {}
    for name in CHECKED_FACTS:
        fact = fields.get(name)
        if fact is not None and fact.status == "found":
            payload[name] = {"value": fact.value, "raw_value": fact.raw_value,
                             "reference_event": fact.reference_event, "conditions": list(fact.conditions),
                             "quoted": [e.text for e in fact.evidence]}
    return payload


def verify(document, fields, model, key, timeout=180.0):
    facts = fact_payload(fields)
    pages = [{"page_number": p.page_number, "original_text": p.text} for p in document.pages]
    body = {"model": model, **sampling_options(model), "max_tokens": 4096,
            "messages": [{"role": "system", "content": PROMPT},
                         {"role": "user", "content": json.dumps({"pages": pages, "facts": facts}, ensure_ascii=False)}],
            "response_format": {"type": "json_schema",
                                "json_schema": {"name": "verification", "strict": True, "schema": SCHEMA}},
            "provider": provider_preferences()}
    request = Request(URL, data=json.dumps(body).encode("utf-8"), method="POST",
                      headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    with urlopen(request, timeout=timeout) as reply:
        response = parse_json(reply.read().decode("utf-8"))
    checks = parse_json(response["choices"][0]["message"]["content"])["checks"]
    page_text = "\n".join(p.text for p in document.pages)
    for check in checks:
        # A flagged qualifier only counts as grounded if it is really in the document.
        check["grounded"] = bool(check["missing_text"]) and locate_excerpt(check["missing_text"], page_text) is not None
    return checks, response.get("model"), response.get("provider"), response.get("usage")


def main():
    load_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path, help="Saved extraction run JSON")
    parser.add_argument("--model", default=os.environ.get("OPENROUTER_MODEL", "qwen/qwen3-14b"))
    arguments = parser.parse_args()
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("OPENROUTER_API_KEY is not set.")
    saved = parse_json(arguments.run.read_text(encoding="utf-8"))
    document = read_pdf(Path(saved["document"]["source_path"].replace("\\", "/")))
    run = read_run(arguments.run, document)
    print(f"{document.source_path.name}  verifier model: {arguments.model}")
    checks, served, host, usage = verify(document, run.fields, arguments.model, key)
    for check in checks:
        fact = run.fields[check["fact"]]
        print(f"  {check['fact']:16} {check['verdict']:18} grounded={check['grounded']!s:5} "
              f"extracted={fact.value}/{fact.reference_event}/{list(fact.conditions)}")
        if check["verdict"] != "supported":
            print(f"      missing_text: {check['missing_text']!r}\n      reason: {check['reason']}")
    print(f"  served by {host} ({served}); usage {usage}")


if __name__ == "__main__":
    main()
