"""Ingestion: document -> chunks -> Moss. The WRITE side."""

from pathlib import Path

from moss import DocumentInfo

from . import chunking, config, moss_store


async def run(path: str, index: str, client_id: str | None) -> tuple[int, str]:
    """Ingest one file into `index`, optionally tagged for `client_id`. Returns (n_chunks, source)."""
    source = Path(path).stem
    pages = chunking.extract_pages(path)
    if sum(len(p) for p in pages) == 0:
        raise SystemExit(
            f"Extracted 0 characters from {path}. "
            "If it's a scanned/image-only PDF, pypdf can't OCR it."
        )

    chunks = chunking.chunk_pages(source, pages, config.CHUNK_WORDS, config.CHUNK_OVERLAP)
    prefix = f"{client_id}::" if client_id else ""
    docs = [
        DocumentInfo(
            id=f"{prefix}{c['id']}",  # client-prefixed so ids stay unique in a shared index
            text=c["text"],
            metadata={
                "page": c["page"],
                "source": c["source"],
                **({"client_id": client_id} if client_id else {}),
            },
        )
        for c in chunks
    ]
    await moss_store.write_docs(index, docs, config.MODEL_ID)
    return len(chunks), source
