"""Phase 2 — client stub for the Cloud AI 100 reranking/generation step.

Phase 2 stub: does no real reranking or LLM generation (the actual
Qualcomm AI SDK client lands in Phase 3's cloud/inference.py, wired in
here). Passes candidates through in their incoming order (already
distance-sorted by vector_store.search()) and synthesizes a simple
templated answer referencing the top candidate.

Input: a query string + the top-k candidate chunk rows from
VectorStore.search().
Output: {"answer": str, "ranked_sources": list[dict]} — matches the real
Phase 3 client's output contract so routes_query.py doesn't change shape
when the stub is swapped out.
Side effects: none (no network call in this stub).
"""

_EXCERPT_MAX_CHARS = 200


def rerank_and_generate(query, candidates):
    """Phase 2 stub for Cloud AI 100 reranking + answer generation.

    Args:
        query: the original user query text.
        candidates: list of chunk row dicts (from VectorStore.search()),
            already ordered nearest-first.

    Returns:
        {"answer": str, "ranked_sources": list[dict]}. `ranked_sources` is
        `candidates` unchanged (no real reranking yet — Phase 3 replaces
        this). `answer` is a templated string built from the top
        candidate's chunk text, or a "no relevant results" message if
        candidates is empty.
    """
    if not candidates:
        return {
            "answer": f'No relevant results found for "{query}".',
            "ranked_sources": [],
        }

    top = candidates[0]
    excerpt = (top.get("chunk") or "").strip()
    if len(excerpt) > _EXCERPT_MAX_CHARS:
        excerpt = excerpt[:_EXCERPT_MAX_CHARS].rstrip() + "..."

    title = top.get("title") or "an indexed document"
    answer = f'Based on "{title}": {excerpt}' if excerpt else f'Found a match in "{title}".'

    return {"answer": answer, "ranked_sources": candidates}
