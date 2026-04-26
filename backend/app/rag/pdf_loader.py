from pathlib import Path

import fitz


def extract_pdf_text(path: Path) -> list[dict[str, str | int]]:
    pages: list[dict[str, str | int]] = []
    with fitz.open(path) as doc:
        for index, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if text:
                pages.append({"page": index, "text": text})
    if not pages:
        raise ValueError("No selectable text found in the PDF.")
    return pages
