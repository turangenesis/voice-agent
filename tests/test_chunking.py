"""Pure unit tests for the chunker — no network, run anywhere: `pytest` or the assert-runner below."""

from voiceagent.chunking import chunk_pages


def test_ids_and_count():
    pages = [" ".join(f"w{i}" for i in range(1000))]  # 1000 words
    chunks = chunk_pages("doc", pages, size=800, overlap=100)
    # step = 700 -> windows at start 0 and 700 -> 2 chunks
    assert len(chunks) == 2
    assert chunks[0]["id"] == "doc::p1::c0"
    assert chunks[1]["id"] == "doc::p1::c1"
    assert chunks[0]["source"] == "doc"


def test_overlap_words_shared():
    pages = [" ".join(f"w{i}" for i in range(1000))]
    chunks = chunk_pages("doc", pages, size=800, overlap=100)
    w0 = chunks[0]["text"].split()
    w1 = chunks[1]["text"].split()
    assert w0[-100:] == w1[:100]  # the overlap region is genuinely shared


def test_empty_pages_skipped():
    assert chunk_pages("doc", ["", "   "], size=800, overlap=100) == []


if __name__ == "__main__":
    test_ids_and_count()
    test_overlap_words_shared()
    test_empty_pages_skipped()
    print("✓ all chunking tests passed")
