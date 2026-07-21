"""INTERFACE layer — the `voiceagent` command. Thin: parse args, call core, hand off.

    voiceagent ingest <file> [--index docs] [--client acme]
    voiceagent talk           [--index docs] [--client acme] [--mode console|dev|start]
"""

import argparse
import asyncio
import os
import sys


def main() -> None:
    parser = argparse.ArgumentParser(prog="voiceagent", description="Docs -> Moss -> voice agent.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="Load a document (.pdf/.md/.txt) into a Moss index.")
    p_ingest.add_argument("path", help="path to the document")
    p_ingest.add_argument("--index", default=os.getenv("MOSS_INDEX", "docs"), help="Moss index (default: docs)")
    p_ingest.add_argument("--client", default=None, help="tag docs with a client id (share one index across clients)")

    p_talk = sub.add_parser("talk", help="Start the voice agent and talk to it.")
    p_talk.add_argument("--index", default=os.getenv("MOSS_INDEX", "docs"), help="Moss index to read (default: docs)")
    p_talk.add_argument("--client", default=None, help="scope answers to one client's docs")
    p_talk.add_argument("--mode", default="console", choices=["console", "dev", "start"], help="LiveKit run mode")

    args = parser.parse_args()

    if args.command == "ingest":
        from . import ingest

        n, source = asyncio.run(ingest.run(args.path, args.index, args.client))
        scope = f" for client '{args.client}'" if args.client else ""
        print(f"✓ ingested {n} chunks from '{source}' into Moss '{args.index}'{scope}")

    elif args.command == "talk":
        # The agent reads these from the environment at query time.
        os.environ["MOSS_INDEX"] = args.index
        if args.client:
            os.environ["VOICEAGENT_CLIENT"] = args.client
        # LiveKit's cli.run_app parses sys.argv itself; hand it the chosen mode.
        sys.argv = ["voiceagent", args.mode]
        from . import agent

        agent.run_console()
