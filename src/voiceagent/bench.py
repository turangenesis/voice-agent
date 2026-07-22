"""Measure ingestion + retrieval speed — turns 'is it fast? does it scale?' into numbers.

    op run --env-file=.env -- python3 -m voiceagent.bench --docs 100 --queries 20

Writes synthetic docs into a throwaway index, times the write and a batch of queries,
prints docs/sec and query latency, then deletes the index (Moss free tier caps at 3).
"""

import argparse
import asyncio
import time

from moss import DocumentInfo

from . import config, moss_store


async def run(n_docs: int, queries: int, index: str, keep: bool) -> None:
    docs = [
        DocumentInfo(
            id=f"bench-{i}",
            text=f"Record {i}: the access code for unit {i} is {1000 + i}; it ships in {i % 30} days and covers region {i % 7}.",
            metadata={"source": "bench"},
        )
        for i in range(n_docs)
    ]

    t0 = time.perf_counter()
    await moss_store.write_docs(index, docs, config.MODEL_ID)
    ingest_s = time.perf_counter() - t0

    latencies = []
    for q in range(queries):
        s = time.perf_counter()
        await moss_store.retrieve_texts(index, f"access code for unit {q * 3}", top_k=5)
        latencies.append((time.perf_counter() - s) * 1000)
    latencies.sort()

    def pct(p: float) -> float:
        return latencies[min(len(latencies) - 1, int(len(latencies) * p))]

    print("\n=== voice-agent benchmark ===")
    print(f"ingest:    {n_docs} docs in {ingest_s:.2f}s  =  {n_docs / ingest_s:.0f} docs/sec")
    print(f"retrieval: {queries} queries  ->  median {pct(0.5):.0f} ms | p95 {pct(0.95):.0f} ms")
    print(f"(Moss holds ~100k docs per index; this measured {n_docs}.)")

    if keep:
        print(f"kept index '{index}'")
    else:
        await moss_store.delete_index(index)
        print(f"cleaned up index '{index}'")


def main() -> None:
    ap = argparse.ArgumentParser(prog="voiceagent-bench")
    ap.add_argument("--docs", type=int, default=100)
    ap.add_argument("--queries", type=int, default=20)
    ap.add_argument("--index", default="bench")
    ap.add_argument("--keep", action="store_true", help="don't delete the index afterward")
    args = ap.parse_args()
    asyncio.run(run(args.docs, args.queries, args.index, args.keep))


if __name__ == "__main__":
    main()
