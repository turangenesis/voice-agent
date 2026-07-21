"""Pure text extraction + chunking. No network, no Moss — fully unit-testable."""

from pathlib import Path

from pypdf import PdfReader

TEXT_SUFFIXES = {".md", ".markdown", ".txt", ".text"}


def extract_pages(path: str) -> list[str]:
    """Return text as a list of 'pages'. PDFs -> one entry per page; text/MD -> one entry."""
    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(path)
        return [(page.extract_text() or "").strip() for page in reader.pages]
    if suffix in TEXT_SUFFIXES:
        return [Path(path).read_text(encoding="utf-8", errors="replace").strip()]
    raise ValueError(f"Unsupported file type '{suffix}'. Supported: .pdf, .md, .txt")


def chunk_pages(source: str, pages: list[str], size: int, overlap: int) -> list[dict]:
    """Word-window chunks with overlap, one id per (page, chunk)."""
    step = max(1, size - overlap)
    chunks: list[dict] = []
    for page_no, page_text in enumerate(pages, start=1):
        words = page_text.split()
        if not words:
            continue
        start = 0
        cid = 0
        while start < len(words):
            window = words[start : start + size]
            chunks.append(
                {
                    "id": f"{source}::p{page_no}::c{cid}",
                    "text": " ".join(window),
                    "page": str(page_no),
                    "source": source,
                }
            )
            cid += 1
            if start + size >= len(words):
                break
            start += step
    return chunks
