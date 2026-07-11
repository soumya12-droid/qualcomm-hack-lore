"""Phase 1 — splits extracted document text into overlapping chunks for embedding.

Input: raw text extracted from a document (see extractor.py).
Output: list of {"text": str, "chunk_index": int} dicts, in document order.
Side effects: none.
"""

import re

_TOKEN_RE = re.compile(r"\S+")

DEFAULT_CHUNK_SIZE = 512
DEFAULT_OVERLAP_RATIO = 0.125  # 12.5%, within the 10-15% target from CLAUDE.md


def chunk_text(text, chunk_size=DEFAULT_CHUNK_SIZE, overlap_ratio=DEFAULT_OVERLAP_RATIO):
    """Split `text` into overlapping windows of whitespace-delimited tokens.

    Args:
        text: raw extracted document text.
        chunk_size: target tokens per chunk (word-based approximation of the
            ~512 "tokens" target — no model tokenizer dependency in Phase 1).
        overlap_ratio: fraction of each window that overlaps with the next,
            in [0, 1).

    Returns:
        List of {"text": str, "chunk_index": int} dicts. `text` is a raw
        substring of the input (whitespace/newlines preserved as-is), so it
        matches the "chunk" field's "raw chunk text" contract in the LanceDB
        schema. Empty/whitespace-only input returns [].
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if not (0 <= overlap_ratio < 1):
        raise ValueError("overlap_ratio must be in [0, 1)")

    tokens = list(_TOKEN_RE.finditer(text))
    if not tokens:
        return []

    overlap = int(chunk_size * overlap_ratio)
    stride = max(chunk_size - overlap, 1)

    chunks = []
    chunk_index = 0
    start = 0
    n = len(tokens)
    while start < n:
        end = min(start + chunk_size, n)
        chunk_start_char = tokens[start].start()
        chunk_end_char = tokens[end - 1].end()
        chunks.append({
            "text": text[chunk_start_char:chunk_end_char],
            "chunk_index": chunk_index,
        })
        chunk_index += 1
        if end == n:
            break
        start += stride

    return chunks
