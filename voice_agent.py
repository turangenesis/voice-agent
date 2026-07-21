"""
voice_agent.py — LiveKit voice agent. The READ side of the pipeline.

Talks to you and answers questions about an ingested document by reading a Moss
index (filled by ingest.py). Runs on LiveKit Inference for STT/LLM/TTS, so it
needs LiveKit keys but NO separate OpenAI account.

The agent is deliberately dumb about WHERE the data came from — it only reads
Moss and decides what to retrieve. Swap ingest.py's source (PDF → scrape → MCP)
and this file never changes.

Adapted from slot-sniper/voice_agent.py (index 'slots' → 'docs', tool + instructions changed).

Setup:
  1) lk cloud auth                         # free LiveKit account + keys
  2) put these in voice-agent/.env:
       LIVEKIT_URL=wss://...
       LIVEKIT_API_KEY=...
       LIVEKIT_API_SECRET=...
       MOSS_PROJECT_ID=...  MOSS_PROJECT_KEY=...
  3) run:
       source .venv/bin/activate
       set -a; source .env; set +a
       python3 voice_agent.py console       # talk to it in the terminal
"""

import os

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    function_tool,
    inference,
)
from livekit.plugins import silero
from moss import MossClient, QueryOptions

STT_MODEL = os.getenv("LIVEKIT_STT_MODEL", "deepgram/nova-3")
LLM_MODEL = os.getenv("LIVEKIT_LLM_MODEL", "openai/gpt-4.1-mini")
TTS_MODEL = os.getenv("LIVEKIT_TTS_MODEL", "cartesia/sonic-3")
TTS_VOICE = os.getenv("LIVEKIT_TTS_VOICE", "")
MOSS_INDEX = os.getenv("MOSS_INDEX", "docs")


async def _query_raw(question: str, top_k: int = 5) -> list:
    """Return the raw matching docs (with .text and .metadata) for a query."""
    client = MossClient(os.environ["MOSS_PROJECT_ID"], os.environ["MOSS_PROJECT_KEY"])
    try:
        await client.load_index(MOSS_INDEX)
        result = await client.query(MOSS_INDEX, question, QueryOptions(top_k=top_k))
    except Exception:
        return []
    return getattr(result, "docs", None) or []


async def _retrieve(question: str, top_k: int = 5) -> list[str]:
    """Read the most relevant chunk texts for `question` from the Moss index."""
    return [text for doc in await _query_raw(question, top_k) if (text := getattr(doc, "text", "")).strip()]


class DocsAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions=(
                "You are a helpful voice assistant that answers questions about a specific set "
                "of documents. When the user asks what you know, what you can help with, or what "
                "you have access to, call the describe_documents tool and tell them what's loaded. "
                "For any question about the content, call search_document and answer using ONLY "
                "what it returns. Keep replies short and spoken-friendly. If a search returns "
                "nothing relevant, say plainly that the documents don't cover that — never make "
                "anything up."
            )
        )

    @function_tool()
    async def search_document(self, question: str) -> str:
        """Search the ingested documents for information relevant to the user's question."""
        chunks = await _retrieve(question)
        if not chunks:
            return "No relevant information found in the documents."
        return "\n\n".join(chunks)

    @function_tool()
    async def describe_documents(self) -> str:
        """Describe what documents and topics are loaded. Use when the user asks what you know
        or what you can help with, rather than asking about specific content."""
        docs = await _query_raw("overview summary main topics", top_k=8)
        if not docs:
            return "No documents are loaded yet, so I don't have anything to answer from."
        sources = sorted({(getattr(d, "metadata", None) or {}).get("source", "") for d in docs} - {""})
        preview = " ".join(getattr(d, "text", "")[:200] for d in docs[:3]).strip()
        label = ", ".join(sources) if sources else "an unnamed document"
        return f"I have access to: {label}. A sample of the content: {preview}"


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    tts = inference.TTS(model=TTS_MODEL, voice=TTS_VOICE) if TTS_VOICE else inference.TTS(model=TTS_MODEL)
    session = AgentSession(
        stt=inference.STT(model=STT_MODEL),
        llm=inference.LLM(model=LLM_MODEL),
        tts=tts,
        vad=ctx.proc.userdata["vad"],
    )
    await session.start(agent=DocsAgent(), room=ctx.room)
    await ctx.connect()
    await session.generate_reply(
        instructions="Greet the user in one short sentence and offer to answer questions about the document."
    )


if __name__ == "__main__":
    cli.run_app(server)
