"""Block 2: read native PDF text and keep page references for later evidence."""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import pymupdf


class PdfReadError(ValueError):
    """The document cannot be read safely and needs human attention."""


@dataclass(frozen=True)
class PdfPage:
    """One page's number and unchanged text returned by the PDF library."""

    page_number: int
    text: str


@dataclass(frozen=True)
class PdfDocument:
    """The source file, every page, and any known extraction problems."""

    source_path: Path
    pages: tuple[PdfPage, ...]
    issues: tuple[str, ...]


def read_pdf(path: Path) -> PdfDocument:
    """Extract native text; do not interpret terms or make supplier decisions."""
    source_path = Path(path).expanduser().resolve()
    if not source_path.is_file():
        raise PdfReadError(f"PDF file not found or not a regular file: {source_path}")

    pages = []
    issues = []

    try:
        # The with block closes the document even if extraction fails.
        with pymupdf.open(source_path) as pdf:
            if not pdf.is_pdf:
                raise PdfReadError(f"Not a PDF document: {source_path.name}")
            if pdf.needs_pass:
                raise PdfReadError(f"PDF needs a password: {source_path.name}")
            if pdf.page_count == 0:
                raise PdfReadError(f"PDF has no pages: {source_path.name}")

            if pdf.is_repaired:
                issues.append("PDF required repair during opening; human review required.")

            for page_number, page in enumerate(pdf, start=1):
                # Keep native content order and whitespace for later evidence.
                text = page.get_text("text", sort=False)
                pages.append(PdfPage(page_number=page_number, text=text))

                # Check for empty text without changing the stored text.
                if not text.strip():
                    issues.append(
                        f"Page {page_number} has no selectable text; "
                        "human review or OCR is required."
                    )

    except PdfReadError:
        raise
    except (OSError, RuntimeError, ValueError, pymupdf.FileDataError) as error:
        raise PdfReadError(f"Cannot read PDF {source_path.name}: {error}") from error

    return PdfDocument(
        source_path=source_path,
        pages=tuple(pages),
        issues=tuple(issues),
    )


def main() -> int:
    """Preview one or more files; return 1 if any extraction needs attention."""
    parser = argparse.ArgumentParser(description="Read PDF text with page references.")
    parser.add_argument("paths", nargs="+", type=Path, help="PDF files to read.")
    parser.add_argument("--summary", action="store_true", help="Hide full page text.")
    arguments = parser.parse_args()
    needs_attention = False

    for path in arguments.paths:
        try:
            document = read_pdf(path)
        except PdfReadError as error:
            print(f"Extraction error: {error}", file=sys.stderr)
            needs_attention = True
            continue

        print(
            f"PDF: {document.source_path.name} | Pages: {len(document.pages)} "
            f"| Extraction issues: {len(document.issues)}"
        )

        if not arguments.summary:
            for page in document.pages:
                print(f"\nPage {page.page_number}")
                print(page.text)

        for issue in document.issues:
            print(f"Extraction issue: {issue}")
            needs_attention = True

    if needs_attention:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
