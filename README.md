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

| Version | Adds | Trigger |
|---|---|---|
| v1 | scripts | `python script.py` |
| **v2 (now)** | installable `voiceagent` command, `src/` package, multi-client, tests + eval, `ARCHITECTURE.md` | `voiceagent ingest` / `voiceagent talk` |
| v3 | `api.py` (FastAPI) wrapping the same core; CI + Dockerfile | HTTP endpoint |
| v4 | thin web UI (e.g. button in a hosted PDF) that calls the v3 API | click → talk (zero logic in UI) |

## Reuse notes

Reused from `hackersquad/slot-sniper` (voice agent + Moss write) and `rag-assistant` (chunking).
