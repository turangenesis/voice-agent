# voice-agent

A minimal **docs → Moss → voice agent**: drop a PDF, ingest it, then talk to a
LiveKit voice agent that answers questions from that PDF's content.

The two sides are decoupled by design:
- **`ingest.py`** — the *write* side. Anything can write to Moss (PDF now; scrape / MCP / live loop later).
- **`voice_agent.py`** — the *read* side. It only ever reads Moss and decides what to retrieve. Swapping the ingestion source never touches it.

## Setup (once)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

lk cloud auth          # free LiveKit account → paste LIVEKIT_URL/API_KEY/API_SECRET into .env
```

`.env` already has the Moss keys. You only need to add the three LiveKit values.

## Use

```bash
source .venv/bin/activate
set -a; source .env; set +a

python3 ingest.py path/to/document.pdf      # PDF → chunks → Moss 'docs' index
python3 voice_agent.py console              # talk to it; ask about the document
```

Ask something in the PDF → it answers from the content. Ask something not in it →
it tells you the document doesn't cover that (no hallucination).

## Notes

- v1 scope is only PDF → Moss → voice answers. No scraping, MCP, or web UI yet.
- Scanned/image-only PDFs won't work — pypdf can't OCR. `ingest.py` fails loudly if it extracts 0 characters.
- Reused from `hackersquad/slot-sniper` (voice agent + Moss write pattern) and `rag-assistant` (chunking idea).
