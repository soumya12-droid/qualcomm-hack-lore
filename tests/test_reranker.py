from cloud.reranker import rerank


def test_empty_candidates_returns_empty_list():
    assert rerank([1.0, 0.0], []) == []


def test_single_candidate_returned_unchanged():
    candidates = [{"title": "a", "embedding": [1.0, 0.0]}]
    assert rerank([1.0, 0.0], candidates) == candidates


def test_reorders_by_descending_cosine_similarity():
    query = [1.0, 0.0]
    candidates = [
        {"title": "orthogonal", "embedding": [0.0, 1.0]},   # similarity 0
        {"title": "exact_match", "embedding": [1.0, 0.0]},  # similarity 1
        {"title": "close", "embedding": [0.9, 0.1]},         # similarity ~0.994
    ]

    result = rerank(query, candidates)

    assert [c["title"] for c in result] == ["exact_match", "close", "orthogonal"]


def test_opposite_direction_ranks_last():
    query = [1.0, 0.0]
    candidates = [
        {"title": "opposite", "embedding": [-1.0, 0.0]},  # similarity -1
        {"title": "match", "embedding": [1.0, 0.0]},       # similarity 1
    ]

    result = rerank(query, candidates)

    assert [c["title"] for c in result] == ["match", "opposite"]


def test_ties_preserve_original_relative_order():
    query = [1.0, 0.0]
    candidates = [
        {"title": "first", "embedding": [2.0, 0.0]},   # same direction, similarity 1
        {"title": "second", "embedding": [5.0, 0.0]},  # same direction, similarity 1
    ]

    result = rerank(query, candidates)

    assert [c["title"] for c in result] == ["first", "second"]


def test_missing_embedding_field_scores_lowest():
    query = [1.0, 0.0]
    candidates = [
        {"title": "no_embedding"},
        {"title": "has_embedding", "embedding": [1.0, 0.0]},
    ]

    result = rerank(query, candidates)

    assert [c["title"] for c in result] == ["has_embedding", "no_embedding"]


def test_does_not_mutate_input_list_or_dicts():
    query = [1.0, 0.0]
    candidates = [
        {"title": "b", "embedding": [0.0, 1.0]},
        {"title": "a", "embedding": [1.0, 0.0]},
    ]
    original = [dict(c) for c in candidates]

    rerank(query, candidates)

    assert candidates == original
