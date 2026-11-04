"""Extract explicit contract components; unexplained language remains unresolved."""

import re
from decimal import Decimal

from procurement.extraction import Evidence, preview, resolve_field
from procurement.pdf_text import PdfDocument

FIELD_NAMES = ("advance_percent", "payment_days", "delivery_days", "penalty_clause",
               "penalty_percent", "penalty_basis", "validity_days")
SECTION_NAMES = {"payment": "payment", "payment terms": "payment", "delivery": "delivery",
                 "delivery terms": "delivery", "shipping": "delivery", "delay": "penalty",
                 "penalty": "penalty", "late delivery": "penalty", "validity": "validity",
                 "quotation validity": "validity"}
HEADINGS = re.compile(r"^(?:\d+[.)]\s*)?(?P<label>[A-Za-z][A-Za-z /-]{1,40})[.:][ \t]+", re.M)
PERCENT = r"[0-9]+(?:\.[0-9]+)?"
DURATION = re.compile(r"(?<![\w.,+-])(?P<number>[0-9]+)\s+(?P<unit>days?|weeks?)\b", re.I)
REFERENCE = re.compile(r"\b(?:after|of|from)\s+(?:receiving\s+|the\s+date\s+of\s+)?(?:the\s+)?"
                       r"(?P<event>purchase order|PO|delivery|quotation date|date above)\b", re.I)
FILLER = {"a", "an", "the", "this", "is", "be", "will", "shall"}


def _supported_words(text: str, vocabulary: set) -> bool:
    """Every remaining token must have a known role; do not ignore qualifications."""
    words = re.findall(r"\w+|[^\w\s.,:;()%]", text.casefold())
    return all(word in vocabulary | FILLER for word in words)


def _duration(text: str, expected_event: str) -> tuple[list[str], str | None]:
    intervals = list(DURATION.finditer(text))
    anchors = list(REFERENCE.finditer(text))
    if len(intervals) != 1 or len(anchors) != 1:
        return [], None
    interval,anchor = intervals[0],anchors[0]
    event = anchor.group('event').casefold()
    event = {"po": "purchase_order", "purchase order": "purchase_order",
             "date above": "quotation_date", "quotation date": "quotation_date"}.get(event,event)
    if event != expected_event:
        return [], event
    operator = "for" if expected_event == 'quotation_date' else "within"
    # The operator must govern the duration, not merely appear elsewhere.
    if not re.search(rf"\b{operator}\s*$", text[:interval.start()], re.I):
        return [], event
    remaining = text[:interval.start()] + ' ' + text[interval.end():]
    remaining = REFERENCE.sub(' ',remaining)
    vocabulary = {
        'delivery':{'within','payment','full','balance','remaining','payable'},
        'purchase_order':{'within','delivery','delivered','deliver','goods','arrive','arrival'},
        'quotation_date':{'for','quotation','quote','valid','validity'},
    }[expected_event]
    if not _supported_words(remaining,vocabulary):
        return [], event
    days = int(interval.group('number')) * (7 if interval.group('unit').lower().startswith('week') else 1)
    return [str(days)],event


def _advance(text: str) -> list[str]:
    if re.fullmatch(r"(?:no|zero)\s+(?:advance|prepayment)(?:\s+payment)?(?:\s+required)?",text,re.I):
        return ['0']
    advance = re.compile(rf"(?<![\w.,+-])(?P<rate>{PERCENT})%\s+(?:advance|prepayment)\b",re.I)
    rates = [match.group('rate') for match in advance.finditer(text)]
    remaining = advance.sub('advance',text)
    if not _supported_words(remaining,{"advance","prepayment","payment","payable","required","with","purchase","order","po"}):
        return []
    return rates


def _penalty(text: str) -> dict:
    # Absence must be an explicit statement, never inferred from missing headings.
    if re.fullmatch(r"(?:none|not applicable|no (?:late delivery )?penalty(?: applies|required)?)\.?",text,re.I):
        return {'penalty_clause':['absent']}
    rates = re.findall(rf"(?<![\w.,+-])({PERCENT})%",text)
    remaining = re.sub(rf"(?<![\w.,+-]){PERCENT}%",' ',text)
    vocabulary = {"late","delivery","delay","penalty","for","supplier","pay","in","attract",
                  "of","order","value","per","each","full","week"}
    if len(rates) != 1 or not _supported_words(remaining,vocabulary):
        return {}
    result = {'penalty_clause':['present'],'penalty_percent':rates}
    if re.search(r"\bof (?:the )?order value\b",text,re.I) and re.search(r"\b(?:per|each(?: full)?) week\b",text,re.I):
        result['penalty_basis'] = ['order_value_per_week']
    return result


def extract_terms(document: PdfDocument) -> dict:
    """Locate labelled clauses, extract components, and preserve uncertain source text."""
    extra = ('payment_clause_text','delivery_clause_text','penalty_clause_text','validity_clause_text',
             'payment_reference','delivery_reference','validity_reference')
    candidates = {name: [] for name in FIELD_NAMES + extra}
    unsupported = {name: [] for name in FIELD_NAMES + extra}
    clause_fields = {'payment':('advance_percent','payment_days'), 'delivery':('delivery_days',),
                     'validity':('validity_days',), 'penalty':('penalty_clause','penalty_percent','penalty_basis')}
    for page in document.pages:
        headings = list(HEADINGS.finditer(page.text))
        for index,heading in enumerate(headings):
            kind = SECTION_NAMES.get(heading.group('label').casefold())
            if kind is None:
                continue
            end = headings[index+1].start() if index+1 < len(headings) else len(page.text)
            raw = page.text[heading.start():end].rstrip()
            excerpt = Evidence(page.page_number,raw)
            candidates[kind+'_clause_text'].append((raw,excerpt))
            body = ' '.join(page.text[heading.end():end].split()).rstrip('.')
            values = {}
            if kind == 'penalty':
                values = _penalty(body)
            elif kind == 'payment':
                advances,balances = [],[]
                unknown_advance = False
                for statement in re.split(r"(?<=[A-Za-z])\.\s+|,\s*(?=balance\b)",body,flags=re.I):
                    if re.search(r"\b(?:advance|prepayment)\b",statement,re.I):
                        found = _advance(statement)
                        advances.extend(found)
                        unknown_advance |= not bool(found)
                    else:
                        balances.append(statement)
                if advances and not unknown_advance:
                    values['advance_percent'] = advances
                payment = ' '.join(balances)
                # Consume a balance percentage only if its relationship to the
                # single agreed advance is explicit and adds up to 100%.
                balances_pattern = rf"\b(balance|remaining)\s+({PERCENT})%"
                portions = re.findall(balances_pattern,payment,re.I)
                if len(portions) == 1 and len(set(advances)) == 1 and not unknown_advance:
                    portion = Decimal(portions[0][1])
                    if 0 <= portion <= 100 and portion+Decimal(advances[0]) == 100:
                        payment = re.sub(balances_pattern,r"\1",payment,flags=re.I)
                days,event = _duration(payment,'delivery')
                values['payment_days'] = days
                if event:
                    candidates['payment_reference'].append((event,excerpt))
            else:
                days,event = _duration(body,'purchase_order' if kind == 'delivery' else 'quotation_date')
                values[kind+'_days'] = days
                if event:
                    candidates[kind+'_reference'].append((event,excerpt))
            for name in clause_fields[kind]:
                if values.get(name):
                    for value in values[name]:
                        candidates[name].append((value,excerpt))
                else:
                    unsupported[name].append(excerpt)
    return {name:resolve_field(candidates[name],unsupported[name]) for name in candidates}


def main() -> int:
    return preview(extract_terms,FIELD_NAMES)


if __name__ == '__main__':
    raise SystemExit(main())
