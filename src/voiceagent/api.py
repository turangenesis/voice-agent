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
from pydantic import BaseModel

from . import ingest, moss_store

app = FastAPI(title="voiceagent", version="0.3.0")


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
    """v3 Path A — return the retrieved chunks (no LLM). `answer` is reserved for Path B."""
    chunks = await moss_store.retrieve_texts(req.index, req.question, req.top_k, req.client)
    return {"question": req.question, "chunks": chunks, "answer": None}


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
