"""Tiny retrieval eval — the scaffold that turns 'vibes' into a number.

Point it at an index/client that already has docs ingested. Each case checks that
retrieval surfaces the expected keyword. Extend EVAL_SET with your own Q/expected
pairs, then run after any prompt/chunking change to catch regressions.

    op run --env-file=.env -- python3 -m voiceagent.eval --index docs [--client acme]
"""

import argparse
import asyncio
import os

from . import moss_store

# (question, a substring that MUST appear in the retrieved text for a pass)
EVAL_SET: list[tuple[str, str]] = [
    # Replace these with facts you know are in your own ingested document:
    ("What are the support hours?", "9"),
    ("What is the refund window?", "30"),
]


async def run(index: str, client_id: str | None) -> int:
    passed = 0
    for question, expected in EVAL_SET:
        texts = await moss_store.retrieve_texts(index, question, top_k=5, client_id=client_id)
        blob = " ".join(texts).lower()
        ok = expected.lower() in blob
        passed += ok
        print(f"[{'PASS' if ok else 'FAIL'}] {question!r} — expected {expected!r}")
    print(f"\n{passed}/{len(EVAL_SET)} passed")
    return passed


def main() -> None:
    parser = argparse.ArgumentParser(prog="voiceagent-eval")
    parser.add_argument("--index", default=os.getenv("MOSS_INDEX", "docs"))
    parser.add_argument("--client", default=None)
    args = parser.parse_args()
    asyncio.run(run(args.index, args.client))


if __name__ == "__main__":
    main()
