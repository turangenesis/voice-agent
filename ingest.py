"""
ingest.py — PDF → Moss. The WRITE side of the pipeline.

Extracts text from a PDF, chunks it, and writes the chunks into a Moss index
that the voice agent reads. This is the only "ingestion" for v1; later it can be
swapped for a scraper / MCP / live loop — the voice agent never changes, because
it only ever reads Moss.

Write pattern (MossClient / DocumentInfo / create_index / add_docs) is lifted
from slot-sniper/seed_moss.py. Chunking idea (word window + overlap, per-page ids)
is adapted from rag-assistant/app/ingest.py.

Run (with the .venv active and .env sourced):
  python3 ingest.py path/to/document.pdf
  python3 ingest.py path/to/document.pdf --index docs
"""

import argparse
import asyncio
import os
from pathlib import Path

from moss import DocumentInfo, MossClient, MutationOptions
from pypdf import PdfReader

CHUNK_WORDS = int(os.getenv("CHUNK_WORDS", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))


def extract_pages(pdf_path: str) -> list[str]:
    """Return the text of each page (empty string for pages pypdf can't read)."""
    reader = PdfReader(pdf_path)
    return [(page.extract_text() or "").strip() for page in reader.pages]


def chunk_pages(source: str, pages: list[str]) -> list[dict]:
    """Word-window chunks with overlap, one id per (page, chunk). Adapted from rag-assistant."""
    step = max(1, CHUNK_WORDS - CHUNK_OVERLAP)
    chunks: list[dict] = []
    for page_no, page_text in enumerate(pages, start=1):
        words = page_text.split()
        if not words:
            continue
        start = 0
        cid = 0
        while start < len(words):
            window = words[start : start + CHUNK_WORDS]
            chunks.append(
                {
                    "id": f"{source}::p{page_no}::c{cid}",
                    "text": " ".join(window),
                    "page": str(page_no),
                    "source": source,
                }
            )
            cid += 1
            if start + CHUNK_WORDS >= len(words):
                break
            start += step
    return chunks


async def write_to_moss(index: str, chunks: list[dict]) -> None:
    client = MossClient(os.environ["MOSS_PROJECT_ID"], os.environ["MOSS_PROJECT_KEY"])
    docs = [
        DocumentInfo(
            id=c["id"],
            text=c["text"],
            metadata={"page": c["page"], "source": c["source"]},
        )
        for c in chunks
    ]
    names = {getattr(i, "name", None) for i in await client.list_indexes()}
    if index in names:
        await client.add_docs(index, docs, MutationOptions(upsert=True))
    else:
        await client.create_index(index, docs, os.getenv("MOSS_MODEL_ID", "moss-minilm"))


async def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a PDF into a Moss index.")
    parser.add_argument("pdf_path", help="path to the PDF to ingest")
    parser.add_argument("--index", default=os.getenv("MOSS_INDEX", "docs"), help="Moss index name (default: docs)")
    args = parser.parse_args()

    source = Path(args.pdf_path).stem
    pages = extract_pages(args.pdf_path)
    total_chars = sum(len(p) for p in pages)
    if total_chars == 0:
        raise SystemExit(
            f"✗ Extracted 0 characters from {args.pdf_path}. "
            "Is it a scanned/image-only PDF? pypdf can't OCR — v1 needs a text PDF."
        )

    chunks = chunk_pages(source, pages)
    print(f"  {len(pages)} pages, {total_chars} chars → {len(chunks)} chunks")
    await write_to_moss(args.index, chunks)
    print(f"✓ ingested {len(chunks)} chunks from '{source}' into Moss '{args.index}' index")


if __name__ == "__main__":
    asyncio.run(main())
