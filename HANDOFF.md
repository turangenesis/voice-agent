# HANDOFF — voice-agent

Reusable base for client voice-agent projects: **docs → Moss → voice/text agent**.
Ingest a document, then ask about it by voice (LiveKit) or by text (HTTP API + web UI).

## Status: v1 → v4 complete, all pushed

| Version | What | State |
|---|---|---|
| v1 | PDF → Moss → LiveKit voice agent | ✅ done, voice loop tested by owner |
| v2 | installable `voiceagent` package (`src/`), multi-client, tests + eval, ARCHITECTURE | ✅ done |
| v3 | FastAPI HTTP API (`/health`, `/ingest`, `/ask`, `/describe`); `/ask` composes a Claude answer | ✅ done, tested live |
| v4 | web UI at `/` — drag-drop + **type or 🎤 talk** (Web Speech → same `/ask` → Claude); Stop button, voice picker, "answered by X" badge | ✅ done, full HTTP stack tested |

Web UI voice = browser speech + **Claude** (no LiveKit in the browser). Terminal `voiceagent talk` = **LiveKit**. Two separate doors; each question uses one brain.

Everything is committed and pushed to `github.com/turangenesis/voice-agent` (private).

## Architecture (see ARCHITECTURE.md)

```
PRESENTATION  static/index.html      — calls /ingest + /ask, no logic
INTERFACE     cli.py (voiceagent)  +  api.py (voiceagent-api)
CORE          chunking.py · moss_store.py · config.py
OPS           ingest.py (write)  ·  agent.py (read, LiveKit voice)
EXTERNAL      Moss (retrieval) · LiveKit (voice LLM) · Claude (text /ask answer)
```
Rule: logic is a library; CLI/API run it; the UI only calls the API. Ingestion ⟂ retrieval — they meet only at a Moss index name (+ optional `client_id`).

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -e ".[test]"
# CLI voice:
op run --env-file=.env -- voiceagent ingest path/to.pdf
op run --env-file=.env -- voiceagent talk
# HTTP API + web UI (open http://127.0.0.1:8000):
op run --env-file=.env -- voiceagent-api
# tests:
python tests/test_chunking.py && python tests/test_api.py
```
Note: `voiceagent` / `voiceagent-api` require the venv active (they live in `.venv/bin/`), or call `./.venv/bin/voiceagent-api`.

## Credentials — 1Password `Dev` vault (no plaintext; `.env` holds only `op://` refs)

- `Moss` (project_id, project_key) — filled ✅
- `LiveKit` (url, api_key, api_secret) — owner reports filled ✅ (voice works)
- `Anthropic` (api_key) — filled ✅ (text `/ask` returns Claude answers; model `claude-haiku-4-5`, cheapest)

## Performance & the benchmark — what we measure and why (important lesson)

`voiceagent.bench` (`op run --env-file=.env -- python3 -m voiceagent.bench`) times ingestion +
retrieval and prints docs/sec and ms/query. Run it to answer "is it fast? does it scale?" with a
**number**, not a guess.

**It caught a real bug in OUR code — not in Moss.** `moss_store.query_docs` called `load_index()`
(an expensive "pull the whole index into memory" op, ~2.4s) on **every** query. Moss did exactly
what we asked — we just asked for the slow thing repeatedly. Fix: load each index **once per
process**, then reuse. Result: warm retrieval **~2,800 ms → ~3 ms** (≈900×).

**The lesson (the whole point):** connecting proven APIs does NOT mean they run optimally. The tools
(Moss, LiveKit, Claude) are fast and correct at *their* job. What you build — the **glue** — decides
performance, cost, and reliability. This bug lived 100% in our retrieval glue (`moss_store.py`), the
*backend of our app*, not in Moss's backend and not in the web frontend. Correct ≠ fast ≠
well-integrated. The engineering value is in *how* you call the tools, and you only see it by
**measuring**. This is a standard, common class of bug (redundant expensive call in a hot path) — most
hackathon demos never measure, so finding+fixing it is a genuine differentiator, not a nicety.

## Gotchas / facts

- Moss free tier caps at **3 indexes**. Currently used: `slots` (from slot-sniper) + `voice_ai-starter-1l22e`. Leave room, or use one shared index with `--client` metadata filtering.
- `op run --env-file=.env` lets `.env` values OVERRIDE shell env vars — pass config via CLI args (`--index`, `--client`), not shell exports.
- `/ask` degrades gracefully: no/invalid Anthropic key → returns chunks with `answer: null`, never 500.
- Multi-client: shared index + `--client` metadata filter (scales to ~100k docs), or `--index` per client (hard isolation, capped at 3).

## Next step (not started): extract the reusable template

The original goal — "build the car, then the factory." Lift this skeleton into:
1. A **template repo** (`voice-agent-template`, GitHub "Use this template") — clone per client, swap index + instructions.
2. Bake the **core→interface→UI + installable entry point** discipline into the owner's `engineering-kit` `plan-feature` flow so all future projects inherit it.

Also open (optional): browser **voice** UI (LiveKit web token endpoint), CI + Dockerfile to deploy, and ingestion adapters (scrapers/MCP/live loops → Moss).

## Owner context (why this exists)

Owner is standardizing on the **core → CLI → API → UI (client)** build order after realizing past projects merged UI with logic. This repo is the first fully correctly-layered instance and the intended template for client work. See the local memory `build-core-cli-first-not-ui` for the working principle.
