"""CORE retrieval layer: the one place that reads/writes Moss.

Both ingest (write) and the agent (read) go through here. Nothing above this
layer talks to Moss directly.
"""

import os

from moss import DocumentInfo, MossClient, MutationOptions, QueryOptions


_CLIENT: MossClient | None = None
_LOADED: set[str] = set()  # indexes already loaded into this process (avoid reloading per query)


def _client() -> MossClient:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = MossClient(os.environ["MOSS_PROJECT_ID"], os.environ["MOSS_PROJECT_KEY"])
    return _CLIENT


async def _ensure_loaded(client: MossClient, index: str) -> None:
    if index not in _LOADED:
        await client.load_index(index)  # once per index per process, not once per query
        _LOADED.add(index)


def _client_filter(client_id: str | None) -> dict | None:
    """Moss metadata filter scoping results to one client. Works on loaded indexes."""
    if not client_id:
        return None
    return {"$and": [{"field": "client_id", "condition": {"$eq": client_id}}]}


async def write_docs(index: str, docs: list[DocumentInfo], model_id: str) -> None:
    """Create the index (first time) or upsert into it."""
    client = _client()
    names = {getattr(i, "name", None) for i in await client.list_indexes()}
    if index in names:
        await client.add_docs(index, docs, MutationOptions(upsert=True))
    else:
        await client.create_index(index, docs, model_id)
    _LOADED.discard(index)  # data changed -> reload on next query so results are fresh


async def delete_index(index: str) -> None:
    """Drop an index (used by the benchmark cleanup). Silent if it doesn't exist."""
    try:
        await _client().delete_index(index)
        _LOADED.discard(index)
    except Exception:
        pass


async def query_docs(index: str, question: str, top_k: int = 5, client_id: str | None = None) -> list:
    """Return raw matching docs. load_index first so metadata filtering runs in-memory."""
    client = _client()
    try:
        await _ensure_loaded(client, index)  # loaded -> QueryOptions(filter=...) is honored, and fast
        options = QueryOptions(top_k=top_k, filter=_client_filter(client_id))
        result = await client.query(index, question, options)
    except Exception:
        return []
    return getattr(result, "docs", None) or []


async def retrieve_texts(index: str, question: str, top_k: int = 5, client_id: str | None = None) -> list[str]:
    docs = await query_docs(index, question, top_k, client_id)
    return [text for doc in docs if (text := getattr(doc, "text", "")).strip()]


async def describe(index: str, client_id: str | None = None) -> str:
    """Human-readable summary of what's loaded — powers the agent's 'what do you know?'."""
    docs = await query_docs(index, "overview summary main topics", top_k=8, client_id=client_id)
    if not docs:
        return "No documents are loaded yet, so I don't have anything to answer from."
    sources = sorted({(getattr(d, "metadata", None) or {}).get("source", "") for d in docs} - {""})
    preview = " ".join(getattr(d, "text", "")[:200] for d in docs[:3]).strip()
    label = ", ".join(sources) if sources else "an unnamed document"
    return f"I have access to: {label}. A sample of the content: {preview}"
