# voice-agent

A minimal **docs → Moss → voice agent**: ingest a document, then talk to a
LiveKit voice agent that answers questions from that document's content.

The two sides are decoupled by design:
- **`ingest.py`** — the *write* side. Anything can write to Moss (files now; scrape / MCP / live loop later).
- **`voice_agent.py`** — the *read* side. It only ever reads Moss and decides what to retrieve. Swapping the ingestion source never touches it.

## Supported documents

`.pdf`, `.md`, `.markdown`, `.txt`. Moss stores plain text, so anything you can
turn into text can be ingested. (Scanned/image-only PDFs won't work — no OCR.)

---

## How to trigger it (this is the current interface — a CLI)

There is **no browser and no UI** — for a voice agent, the terminal *is* the demo.
Run these from one terminal, one after the other:

```bash
# Setup (once)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 1. Load a document into a Moss index (one-shot: it runs, prints ✓, and exits)
op run --env-file=.env -- python3 ingest.py path/to/document.pdf

# 2. Talk to it (this one stays running and listens; Ctrl+C to stop)
op run --env-file=.env -- python3 voice_agent.py console
```

Ask something in the document → it answers out loud. Ask something not in it →
it says the document doesn't cover that (no hallucination).

> To talk to the agent **while** doing other terminal work, use a **second terminal**
> — one terminal = one live process.

---

## Multiple documents & multiple clients — it's all about the INDEX

The agent does **not** read "all of Moss." It reads exactly **one index**, named by
`MOSS_INDEX` (default `docs`). The index name is the entire isolation surface:

```
ingest.py    WRITES → index "acme"        voice_agent  READS ← index "acme"
                         └──────────── they meet only by this name ────────────┘
```

**One client per index — same Moss account, same keys, no new API keys needed:**

```bash
# Client Acme
op run --env-file=.env -- python3 ingest.py acme-handbook.pdf --index acme
MOSS_INDEX=acme op run --env-file=.env -- python3 voice_agent.py console

# Client Globex — fully separate knowledge, same setup
op run --env-file=.env -- python3 ingest.py globex-docs.md --index globex
MOSS_INDEX=globex op run --env-file=.env -- python3 voice_agent.py console
```

Each agent instance only ever sees its own index. Add many documents to one index
by running `ingest.py` multiple times with the same `--index` — Moss holds up to
~100k documents. (Separate API keys per client are only needed for billing/data
isolation, not for keeping agents scoped — the index name already does that.)

---

## Credentials — 1Password (no plaintext secrets)

Secrets live in 1Password's **`Dev`** vault (items `Moss`, `LiveKit`), never in files.
`.env` holds only `op://` **references**, so it's committed on purpose. `op run`
resolves them to real values in memory at runtime.

One-time, get the LiveKit values and store them (or paste them in the 1Password app):

```bash
lk cloud auth                                  # or grab keys from cloud.livekit.io UI
op item edit LiveKit --vault Dev \
  url=wss://YOUR.livekit.cloud \
  api_key=APIxxxx \
  api_secret=xxxx
```

Moss is already stored. Reuse across projects: point any new `.env` at the same
`op://Dev/...` paths — never copy a key again.

---

## Roadmap — how this grows (build in order, never skip to UI)

**Rule:** logic is a library, a CLI/API *runs* it, a UI is *only a client* that calls the API — never put logic in the UI.

| Version | Add | How you trigger it |
|---|---|---|
| **v1 (now)** | two CLI scripts | `python3 ingest.py …` / `voice_agent.py console` — already real, shippable software |
| **v2** | `pyproject.toml` + `[project.scripts]`, then `pip install -e .` | `voiceagent talk` from any terminal — a real installed command |
| **v3** | `api.py` (FastAPI) wrapping the *same* core | any app / web page / phone hits an HTTP endpoint |
| **v4** | a thin web UI (e.g. a button in a hosted PDF) that **calls the v3 API** | click → talk; the UI holds **zero logic** |

This README updates as we build v2 → v4.

---

## Reuse notes

Reused from `hackersquad/slot-sniper` (voice agent + Moss write pattern) and
`rag-assistant` (chunking idea). Concrete-first: this is one working instance;
the reusable template gets extracted only after it's proven.
