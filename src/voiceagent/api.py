"""INTERFACE layer (HTTP) — FastAPI over the same core. v3.

The API holds NO logic — every endpoint calls the same core (ingest / moss_store)
that the CLI and voice agent use. This is what makes the agent reachable by any
client (web page, phone, another service), not just the terminal.

v3 Path A: /ask returns the retrieved chunks. Path B (later) adds a composed
natural-language answer via an LLM.

Run:
    op run --env-file=.env -- voiceagent-api
    # or: op run --env-file=.env -- uvicorn voiceagent.api:app --reload
"""

import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from . import config, ingest, moss_store

app = FastAPI(title="voiceagent", version="0.4.0")

_INDEX_HTML = Path(__file__).parent / "static" / "index.html"


@app.get("/", response_class=HTMLResponse)
async def home() -> str:
    """v4 — the web UI. A pure client: it only calls /ingest and /ask. No logic here."""
    return _INDEX_HTML.read_text(encoding="utf-8")


async def _compose_answer(question: str, chunks: list[str]) -> str:
    """v3 Path B — turn retrieved chunks into a written answer via Claude (cheapest model)."""
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic()  # reads ANTHROPIC_API_KEY from the environment
    context = "\n\n".join(chunks)
    message = await client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=1024,
        system=(
            "Answer the user's question using ONLY the provided document excerpts. "
            "If the excerpts don't contain the answer, say so plainly — never make anything up. "
            "Keep the answer concise."
        ),
        messages=[{"role": "user", "content": f"Document excerpts:\n{context}\n\nQuestion: {question}"}],
    )
    return "".join(block.text for block in message.content if block.type == "text")


@app.get("/health")
async def health() -> dict:
    return {"ok": True}


class AskRequest(BaseModel):
    question: str
    index: str = "docs"
    client: str | None = None
    top_k: int = 5


@app.post("/ask")
async def ask(req: AskRequest) -> dict:
    """Retrieve chunks, and (if an Anthropic key is set) compose a written answer.

    No key yet -> returns chunks with answer=null (Path A). Once the key is added
    to 1Password, the same endpoint starts returning a Claude-written answer (Path B).
    """
    chunks = await moss_store.retrieve_texts(req.index, req.question, req.top_k, req.client)
    answer, source, model = None, ("retrieval" if chunks else "none"), None
    if chunks and config.has_anthropic_key():
        try:
            answer = await _compose_answer(req.question, chunks)
            source, model = "claude", config.ANTHROPIC_MODEL
        except Exception:
            answer = None  # LLM unavailable -> degrade to chunks, never 500
    return {"question": req.question, "chunks": chunks, "answer": answer, "source": source, "model": model}


@app.get("/describe")
async def describe(index: str = "docs", client: str | None = None) -> dict:
    return {"description": await moss_store.describe(index, client)}


@app.post("/ingest")
async def ingest_endpoint(
    file: UploadFile = File(...),
    index: str = Form("docs"),
    client: str | None = Form(None),
) -> dict:
    safe_name = Path(file.filename or "upload.txt").name  # strip any path components
    tmpdir = tempfile.mkdtemp()
    tmp_path = os.path.join(tmpdir, safe_name)
    with open(tmp_path, "wb") as f:
        f.write(await file.read())
    try:
        n, source = await ingest.run(tmp_path, index, client)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
        os.rmdir(tmpdir)
    return {"chunks": n, "source": source, "index": index, "client": client}


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
