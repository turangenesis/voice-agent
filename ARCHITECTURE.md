# Architecture

## The one rule

**Logic is a library. The CLI runs it. (Later: an API runs it; a UI only calls the API.)**
Nothing above the core talks to Moss or LiveKit directly.

## Layers

```
                        ┌─────────────────────────────────────────┐
INTERFACE               │  cli.py   →  `voiceagent ingest / talk`  │
(how you run it)        └──────────────────┬──────────────────────┘
                                           │
OPERATIONS              ┌──────────────────┴──────────────────────┐
(the two things it does)│  ingest.py (write)     agent.py (read)   │
                        └──────────────────┬──────────────────────┘
                                           │
CORE                    ┌──────────────────┴──────────────────────┐
(pure-ish logic)        │  chunking.py     moss_store.py  config.py│
                        └──────────────────┬──────────────────────┘
                                           │
EXTERNAL                        Moss (retrieval)   LiveKit (voice)
```

- **`chunking.py`** — pure text extraction + chunking. No network. Unit-tested (`tests/`).
- **`moss_store.py`** — the *only* place that reads/writes Moss. Both write and read go through it.
- **`config.py`** — env-driven settings (index name, client scope, models).
- **`ingest.py`** — document → chunks → `moss_store.write_docs`.
- **`agent.py`** — LiveKit agent; its tools call `moss_store.retrieve_texts` / `describe`.
- **`cli.py`** — the `voiceagent` command; thin, just parses args and calls the above.
- **`eval.py`** — retrieval eval scaffold; scores an ingested index against known Q/expected pairs.

## Ingestion ⟂ retrieval (decoupled on purpose)

Anything can *write* to Moss (PDF now; scrape / MCP / live loop later). The agent only ever
*reads* Moss. Swapping the ingestion source never touches `agent.py`. They meet only at an
**index name** (and optionally a `client_id`).

## Multi-client model

Two ways to isolate clients — pick per situation:

| Approach | How | When |
|---|---|---|
| **Separate index** | `--index acme` | few clients; hard isolation (Moss free tier caps at 3 indexes) |
| **Shared index + filter** | `--client acme` → tags docs `client_id`, query filters on it | many clients in one index (~100k docs) |

`moss_store.query_docs` applies the filter server-side by loading the index locally first
(Moss only honors metadata filters on loaded indexes).

## Roadmap

- **v2 (this):** installable `voiceagent` command, `src/` package, multi-client, eval + tests, this doc.
- **v3:** `api.py` (FastAPI) wrapping the same core; add CI + Dockerfile for deploy.
- **v4:** a thin web UI (e.g. a button in a hosted PDF) that calls the v3 API — zero logic in the UI.
