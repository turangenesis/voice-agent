"""The LiveKit voice agent. The READ side — only ever reads Moss via moss_store."""

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

from . import config, moss_store


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
        chunks = await moss_store.retrieve_texts(config.index(), question, client_id=config.client_id())
        if not chunks:
            return "No relevant information found in the documents."
        return "\n\n".join(chunks)

    @function_tool()
    async def describe_documents(self) -> str:
        """Describe what documents and topics are loaded. Use when the user asks what you know
        or what you can help with, rather than asking about specific content."""
        return await moss_store.describe(config.index(), client_id=config.client_id())


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    tts = (
        inference.TTS(model=config.TTS_MODEL, voice=config.TTS_VOICE)
        if config.TTS_VOICE
        else inference.TTS(model=config.TTS_MODEL)
    )
    session = AgentSession(
        stt=inference.STT(model=config.STT_MODEL),
        llm=inference.LLM(model=config.LLM_MODEL),
        tts=tts,
        vad=ctx.proc.userdata["vad"],
    )
    await session.start(agent=DocsAgent(), room=ctx.room)
    await ctx.connect()
    await session.generate_reply(
        instructions="Greet the user in one short sentence and offer to answer questions about the documents."
    )


def run_console() -> None:
    """Entry used by `voiceagent talk` (cli.py sets sys.argv to the LiveKit subcommand first)."""
    cli.run_app(server)
