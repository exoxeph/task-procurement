"""Read simple ruled grids by coordinates, independently of PDF insertion order."""

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class PdfTable:
    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    bounds: tuple[float, float, float, float]


# This small vocabulary describes column concepts, not whole supplier templates.
COLUMN_NAMES = {
    "item_code": {"item", "item code", "sku", "code"},
    "description": {"description", "product", "item description"},
    "quantity": {"qty", "quantity"},
    "unit": {"unit", "uom"},
    "unit_price": {"unit price", "price per unit"},
    "line_amount": {"amount", "line total", "line amount"},
}


def item_columns(table: PdfTable) -> dict | None:
    """Recognize column concepts without interpreting cell values or choosing rows."""
    columns = {}
    for index, header in enumerate(table.headers):
        label = re.sub(r"\([^)]*\)", "", header).strip().casefold()
        label = " ".join(label.split())
        for name, aliases in COLUMN_NAMES.items():
            if label in aliases:
                if name in columns:
                    return None
                columns[name] = index
    return columns


def words_to_text(words: list) -> str:
    """Group words into visual lines; keep wrapped cell content on separate lines."""
    lines = []
    baseline = None
    for word in sorted(words, key=lambda word: (round(word[1], 1), word[0])):
        if baseline is None or abs(word[1] - baseline) > 2:
            lines.append([])
            baseline = word[1]
        lines[-1].append(word[4])
    return "\n".join(" ".join(line) for line in lines)


def read_tables(page) -> tuple[PdfTable, ...]:
    """Recognize rectangular grids with shared vertical spans and horizontal rules.

    Borderless/merged/skewed tables are outside this small baseline. No table is
    inferred from a run of text lines. Cell assignment uses word centres.
    """
    vertical = {}
    horizontal = []
    for drawing in page.get_drawings():
        for item in drawing['items']:
            if item[0] != 'l':
                continue
            first, last = item[1], item[2]
            if abs(first.x - last.x) < 0.5:
                span = (round(min(first.y,last.y),1),round(max(first.y,last.y),1))
                vertical.setdefault(span,set()).add(round(first.x,1))
            elif abs(first.y - last.y) < 0.5:
                horizontal.append((round(first.y,1),min(first.x,last.x),max(first.x,last.x)))
    words = page.get_text('words')
    tables = []
    for (top,bottom), boundaries in vertical.items():
        xs = sorted(boundaries)
        if len(xs) < 3:
            continue
        ys = sorted({y for y,left,right in horizontal
                     if top-0.5 <= y <= bottom+0.5 and left <= xs[0]+0.5 and right >= xs[-1]-0.5})
        if len(ys) < 3 or abs(ys[0]-top) > 0.5 or abs(ys[-1]-bottom) > 0.5:
            continue
        rows = []
        for y0,y1 in zip(ys,ys[1:]):
            row = []
            for x0,x1 in zip(xs,xs[1:]):
                cell = [word for word in words if x0 <= (word[0]+word[2])/2 < x1
                        and y0 <= (word[1]+word[3])/2 < y1]
                row.append(words_to_text(cell))
            rows.append(tuple(row))
        tables.append(PdfTable(rows[0],tuple(rows[1:]),(xs[0],top,xs[-1],bottom)))
    return tuple(tables)


def text_outside_tables(page, tables: tuple[PdfTable, ...]) -> str:
    words = []
    for word in page.get_text('words'):
        x,y = (word[0]+word[2])/2,(word[1]+word[3])/2
        if not any(left <= x <= right and top <= y <= bottom for left,top,right,bottom in (table.bounds for table in tables)):
            words.append(word)
    return words_to_text(words)
