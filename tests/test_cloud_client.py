from pc.api.cloud_client import rerank_and_generate


def test_empty_candidates_returns_no_results_message():
    result = rerank_and_generate("neural embeddings research", [])
    assert result["ranked_sources"] == []
    assert "neural embeddings research" in result["answer"]
    assert "No relevant results" in result["answer"]


def test_candidates_are_passed_through_unchanged_and_in_order():
    candidates = [
        {"title": "a.txt", "chunk": "first chunk", "location": "/a.txt"},
        {"title": "b.txt", "chunk": "second chunk", "location": "/b.txt"},
    ]
    result = rerank_and_generate("query", candidates)
    assert result["ranked_sources"] == candidates
    assert result["ranked_sources"][0]["title"] == "a.txt"
    assert result["ranked_sources"][1]["title"] == "b.txt"


def test_answer_references_top_candidate_title_and_excerpt():
    candidates = [{"title": "notes.txt", "chunk": "the hackathon starts July 11", "location": "/notes.txt"}]
    result = rerank_and_generate("when does it start", candidates)
    assert "notes.txt" in result["answer"]
    assert "the hackathon starts July 11" in result["answer"]


def test_long_chunk_text_is_truncated_in_the_answer():
    long_chunk = "word " * 100  # far more than 200 chars
    candidates = [{"title": "long.txt", "chunk": long_chunk, "location": "/long.txt"}]
    result = rerank_and_generate("query", candidates)
    assert result["answer"].endswith("...")
    assert len(result["answer"]) < len(long_chunk)


def test_missing_chunk_text_falls_back_to_generic_answer():
    candidates = [{"title": "empty.txt", "chunk": "", "location": "/empty.txt"}]
    result = rerank_and_generate("query", candidates)
    assert "empty.txt" in result["answer"]


def test_missing_title_falls_back_to_generic_label():
    candidates = [{"chunk": "some content", "location": "/x.txt"}]
    result = rerank_and_generate("query", candidates)
    assert "an indexed document" in result["answer"]


def test_does_not_mutate_input_candidates():
    candidates = [{"title": "a", "chunk": "b", "location": "/a"}]
    original = list(candidates)
    rerank_and_generate("query", candidates)
    assert candidates == original
