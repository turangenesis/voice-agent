# Architecture

## The one rule

**Logic is a library. The CLI runs it. (Later: an API runs it; a UI only calls the API.)**
Nothing above the core talks to Moss or LiveKit directly.

## Layers

```
PRESENTATION            ┌─────────────────────────────────────────┐
(client, no logic)      │  static/index.html → drag-drop + ask      │  ← v4: only calls the API
                        └──────────────────┬──────────────────────┘
                                           │ fetch /ingest, /ask
                        ┌──────────────────┴──────────────────────┐
INTERFACE               │  cli.py  → `voiceagent ingest / talk`     │
(how you run it)        │  api.py  → HTTP: /health /ingest /ask ... │
                        └──────────────────┬──────────────────────┘
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
- **`api.py`** — the `voiceagent-api` HTTP server (FastAPI); thin, each endpoint calls the core. Holds no logic. Also serves the UI at `/`.
- **`static/index.html`** — the v4 web UI. A pure client: `fetch('/ingest')` + `fetch('/ask')`, zero business logic. Proof of the rule.
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

Two independent tracks. The **agent track** deepens *how you reach it*; the **ingestion
track** widens *what it knows*. They never touch each other — both meet only at Moss.

### Agent track — how you reach it
- **v2 (done):** installable `voiceagent` command, `src/` package, multi-client, eval + tests, this doc.
- **v3 — API (done):** `api.py` (FastAPI) over the same core → `GET /health`, `POST /ingest`,
  `POST /ask`, `GET /describe`, served by `voiceagent-api`. **Goal / what you gain:** the agent is
  now reachable by *any* client — a web page, a phone, a client's own system — not just the terminal.
  `/ask` returns retrieved chunks and, when an Anthropic key is present, a Claude-composed answer
  (Path B, `claude-haiku-4-5` by default, gated on `config.has_anthropic_key()` — degrades to chunks
  otherwise). This is the *text* door only; voice composes answers via LiveKit's own LLM. **Next:**
  CI + Dockerfile to deploy.
- **v4 — UI (done):** `static/index.html`, served at `/`, that *calls* the v3 API — drag-and-drop a
  doc (→ `/ingest`), ask questions (→ `/ask`). **Zero logic in the UI.** This is the "show a client,
  no terminal needed" layer. **Next:** a browser *voice* UI (LiveKit token endpoint) as an alternative
  front door, and CI + Dockerfile to host it.

### Ingestion track — what it knows (all write to Moss; the agent never changes)
- PDF / MD / TXT — **done**
- Web scrapers / crawlers (on-demand or continuous) → Moss
- MCP / API connectors (pull from external systems) → Moss
- Live loops (an agent that watches a source and keeps Moss fresh) → Moss

The demo-impressive / hackathon version = several live ingestion sources feeding one voice agent,
with the v4 UI on top. None of it requires changing `agent.py`.

### What actually makes it hireable (do these two, then STOP)

The skeleton (v1–v4) is table stakes — a reusable template now. The *signal* to an employer is not
more layers, it's:

1. **One real integration + one sharp use case.** e.g. Bright Data live-scrapes a real source → Moss,
   and the agent answers about *live* data. Pick ONE concrete story ("voice agent over a client's
   live knowledge base"), not ten half-features.
2. **An evaluation + grading harness.** The impressive part is *measuring* the agent: a test set of
   question→expected-answer, scored automatically, so you can say "accuracy is X%, and here's how I
   improved it." `eval.py` is the seed. This is what separates "I wired an API" from "I built and
   *measured* a system." **This is the differentiator — invest here, not in more UI.**

Diminishing returns (nice, not hireable): more UI polish, more endpoints, more layers.

### Quick UX wins (cheap, worth doing before a demo)
- **Barge-in / Stop button** — cancel `speechSynthesis` mid-answer (right now you can't shut it up).
- **Voice picker** — Web Speech `getVoices()` in the UI; `LIVEKIT_TTS_VOICE` for the terminal path.
- **Which-brain badge** — show "answered by Claude / LiveKit" so it's never ambiguous.
- **Scale/latency numbers** — time ingestion + retrieval, show docs/sec and ms/query (answers "does it
  handle thousands of docs?" — Moss holds ~100k; you just haven't *measured* it yet).

### Building faster next time (the leverage that turns 4 days → ~1 hour)
1. **Spec upfront, then let it run.** State the full goal + definition-of-done in ONE message and let
   the agent execute end-to-end (plan → build all layers → test), instead of gating every step. Biggest lever.
2. **Permission allowlist** in `.claude/settings.json` so routine commands don't prompt. (Ask to set up.)
3. **Reuse this template** — next project starts at v4, not v0.
4. **Loop engineering** — for iterative refinement: state goal + criteria, let it iterate to the bar.
5. **Bake the layering into `engineering-kit`** so core→interface→UI is never re-taught per project.
