# voice-agent

A minimal **docs → Moss → voice agent**: ingest documents, then talk to a
LiveKit voice agent that answers questions from them.

Decoupled by design: **`ingest`** writes to Moss (files now; scrape / MCP / live later),
the **agent** only ever reads Moss. Swapping the ingestion source never touches the agent.
See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the layer map.

## Supported documents

`.pdf`, `.md`, `.markdown`, `.txt`. (Scanned/image-only PDFs won't work — no OCR.)

---

## Setup (once)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .          # installs the `voiceagent` command (see pyproject.toml)
```

`pip install -e .` is what makes `voiceagent` a real command on your PATH.

## Trigger it — the `voiceagent` command

```bash
source .venv/bin/activate

# 1. Load a document (one-shot: runs, prints ✓, exits)
op run --env-file=.env -- voiceagent ingest path/to/document.pdf

# 2. Talk to it (stays running and listens; Ctrl+C to stop)
op run --env-file=.env -- voiceagent talk
```

Ask something in the document → it answers out loud. Ask what it knows → it tells you
what's loaded. Ask something absent → it says the documents don't cover that.

> To talk while doing other terminal work, use a **second terminal** — one terminal = one live process.

---

## Multiple clients — two ways to isolate

The agent reads **one index**, and optionally **one client scope** within it.

**Option A — shared index, filter by client** (scales to many clients, one index holds ~100k docs):

```bash
op run --env-file=.env -- voiceagent ingest acme.pdf   --index shared --client acme
op run --env-file=.env -- voiceagent ingest globex.md  --index shared --client globex

op run --env-file=.env -- voiceagent talk --index shared --client acme    # sees ONLY acme's docs
```

**Option B — separate index per client** (hard isolation; Moss free tier caps at 3 indexes):

```bash
op run --env-file=.env -- voiceagent ingest acme.pdf --index acme
op run --env-file=.env -- voiceagent talk   --index acme
```

Each agent instance only ever sees its scope — verified: another client's data never leaks in.

---

## HTTP API (v3) — reachable by any client

The same core, exposed over HTTP so a web page / phone / another service can call it
(not just the terminal). Start it:

```bash
op run --env-file=.env -- voiceagent-api        # serves on http://127.0.0.1:8000
```

Open **http://127.0.0.1:8000** in a browser for the **web UI (v4)** — drag a file in, ask
questions, read answers. The page is a *pure client*: it only calls `/ingest` and `/ask`,
holds zero logic. The raw endpoints:

```bash
curl localhost:8000/health
# {"ok": true}

curl -F file=@document.pdf -F index=docs localhost:8000/ingest
# {"chunks": 42, "source": "document", "index": "docs", "client": null}

curl -X POST localhost:8000/ask -H 'content-type: application/json' \
  -d '{"question": "What is the refund window?", "index": "docs"}'
# {"question": "...", "chunks": ["...relevant text..."], "answer": null}

curl 'localhost:8000/describe?index=docs'
```

`/ask` returns retrieved chunks and, **once an Anthropic key is set**, also a Claude-written
`answer` (v3 Path B — cheapest model, `claude-haiku-4-5`, ~fractions of a cent per question).
No key → `answer` is `null` and you still get the chunks; it never errors. The voice agent
does **not** use this — it has its own LLM via LiveKit. Interactive docs at `/docs` when running.

**To enable answers:** get a key at console.anthropic.com → open the `Anthropic` item in the
1Password `Dev` vault → paste it into `api_key`. Or:
`op item edit Anthropic --vault Dev api_key=sk-ant-...`. Change the model any time via
`ANTHROPIC_MODEL` in `.env`.

## Tests & eval

```bash
python tests/test_chunking.py                              # pure unit tests, no network
op run --env-file=.env -- python3 -m voiceagent.eval --index docs   # retrieval eval vs known facts
```

Extend `EVAL_SET` in `src/voiceagent/eval.py` with your own question/expected pairs, then
re-run after any prompt or chunking change to catch regressions.

---

## Credentials — 1Password (no plaintext secrets)

Secrets live in 1Password's **`Dev`** vault (items `Moss`, `LiveKit`); `.env` holds only
`op://` references, so it's committed on purpose. `op run` resolves them at runtime.

One-time, store the LiveKit values (or paste them in the 1Password app):

```bash
lk cloud auth                                  # or grab keys from cloud.livekit.io UI
op item edit LiveKit --vault Dev url=wss://YOUR.livekit.cloud api_key=APIxxxx api_secret=xxxx
```

**Free-tier talk time:** ~50 minutes/month (bound by LiveKit Inference credits, ~$2.50).
Idle-but-open barely counts — only active conversation drains it.

---

## Roadmap

**Rule:** logic is a library, the CLI/API runs it, a UI is only a client that calls the API.

**Agent track — how you reach it:**

| Version | Adds | Trigger |
|---|---|---|
| v1 | scripts | `python script.py` |
| **v2 (now)** | installable `voiceagent` command, `src/` package, multi-client, tests + eval, `ARCHITECTURE.md` | `voiceagent ingest` / `voiceagent talk` |
| v3 | `api.py` (FastAPI): `/health`, `/ingest`, `/ask`, `/describe`; `/ask` composes a Claude answer when a key is set | `voiceagent-api` → HTTP, any client |
| **v4 (now)** | web UI at `/` — drag-drop a doc, ask questions; pure client, calls `/ingest` + `/ask` | open `localhost:8000` |
| deploy | CI + Dockerfile | host it |
| voice UI | browser voice (LiveKit token endpoint) | talk in browser |

**Ingestion track — what it knows** (all write to Moss; the agent never changes): PDF/MD/TXT (done)
→ web scrapers → MCP/API connectors → live loops. The impressive/hackathon version = several live
sources feeding one voice agent, with the v4 UI on top. See [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Reuse notes

Reused from `hackersquad/slot-sniper` (voice agent + Moss write) and `rag-assistant` (chunking).
