# voice-agent

A minimal **docs → Moss → voice agent**: drop a PDF, ingest it, then talk to a
LiveKit voice agent that answers questions from that PDF's content.

The two sides are decoupled by design:
- **`ingest.py`** — the *write* side. Anything can write to Moss (PDF now; scrape / MCP / live loop later).
- **`voice_agent.py`** — the *read* side. It only ever reads Moss and decides what to retrieve. Swapping the ingestion source never touches it.

## Credentials — 1Password (no plaintext secrets)

Secrets live in 1Password's **`Dev`** vault (items `Moss`, `LiveKit`), never in files.
`.env` holds only `op://` **references**, so it's committed on purpose. `op run`
resolves them to real values in memory at runtime.

One-time, get the LiveKit values and store them:

```bash
lk cloud auth                                  # free LiveKit account; prints URL + keys
op item edit LiveKit --vault Dev \
  url=wss://YOUR.livekit.cloud \
  api_key=APIxxxx \
  api_secret=xxxx
```

Moss is already stored. Reuse across projects: point any new `.env` at the same
`op://Dev/...` paths — never copy a key again.

## Setup (once)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Use

Every command runs through `op run`, which injects the secrets:

```bash
source .venv/bin/activate

op run --env-file=.env -- python3 ingest.py path/to/document.pdf   # PDF → Moss 'docs'
op run --env-file=.env -- python3 voice_agent.py console           # talk to it
```

Ask something in the PDF → it answers from the content. Ask something not in it →
it tells you the document doesn't cover that (no hallucination).

## Notes

- v1 scope is only PDF → Moss → voice answers. No scraping, MCP, or web UI yet.
- Scanned/image-only PDFs won't work — pypdf can't OCR. `ingest.py` fails loudly if it extracts 0 characters.
- Reused from `hackersquad/slot-sniper` (voice agent + Moss write pattern) and `rag-assistant` (chunking idea).
