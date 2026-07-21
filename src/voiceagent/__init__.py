"""voiceagent — docs -> Moss -> LiveKit voice agent.

Layers (see ARCHITECTURE.md):
  chunking.py + moss_store.py  = CORE (pure-ish logic, importable, no UI)
  ingest.py + agent.py         = the two operations built on the core
  cli.py                       = INTERFACE (the `voiceagent` command)
"""

__version__ = "0.2.0"
