"""Phase 3 — semantic reranking: reorders LanceDB search candidates by
cosine similarity between the query embedding and each candidate's own
embedding vector.

Input: a query embedding + candidate chunk rows (as returned by
VectorStore.search(), each carrying an "embedding" field).
Output: the same candidate dicts, reordered by descending similarity
(stable — ties keep their incoming relative order).
Side effects: none.
"""

import numpy as np


def _cosine_similarity(a, b):
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def rerank(query_embedding, candidates):
    """Reorder candidates by cosine similarity to query_embedding, descending.

    Args:
        query_embedding: list[float], the query's embedding vector.
        candidates: list of dicts, each with an "embedding" field (list[float]).

    Returns:
        A new list containing the same candidate dicts, sorted by
        descending cosine similarity to query_embedding. Ties preserve the
        candidates' original relative order (stable sort). Candidates
        missing (or with an empty) "embedding" field score 0.0.
    """
    if not candidates:
        return []

    scored = [
        (_cosine_similarity(query_embedding, candidate.get("embedding") or []), candidate)
        for candidate in candidates
    ]
    scored.sort(key=lambda pair: -pair[0])
    return [candidate for _, candidate in scored]
