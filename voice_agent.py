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


async def _retrieve(question: str, top_k: int = 5) -> list[str]:
    """Read the most relevant chunks for `question` from the Moss index."""
    client = MossClient(os.environ["MOSS_PROJECT_ID"], os.environ["MOSS_PROJECT_KEY"])
    try:
        await client.load_index(MOSS_INDEX)
        result = await client.query(MOSS_INDEX, question, QueryOptions(top_k=top_k))
    except Exception:
        return []
    return [text for doc in getattr(result, "docs", None) or [] if (text := getattr(doc, "text", "")).strip()]


class DocsAgent(Agent):
    def __init__(self):
        super().__init__(
            instructions=(
                "You are a helpful voice assistant that answers questions about a specific "
                "document. When the user asks anything about the document's content, call the "
                "search_document tool with their question, then answer using ONLY what it returns. "
                "Keep replies short and spoken-friendly. If the search returns nothing relevant, "
                "say plainly that the document doesn't cover that — do not make anything up."
            )
        )

    @function_tool()
    async def search_document(self, question: str) -> str:
        """Search the ingested document for information relevant to the user's question."""
        chunks = await _retrieve(question)
        if not chunks:
            return "No relevant information found in the document."
        return "\n\n".join(chunks)


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
