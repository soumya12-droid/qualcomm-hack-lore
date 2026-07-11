import pytest

from pc.indexer.chunker import chunk_text


def test_empty_input_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   \n\t  ") == []


def test_short_text_returns_single_chunk():
    text = "the quick brown fox jumps over the lazy dog"
    chunks = chunk_text(text, chunk_size=512, overlap_ratio=0.125)
    assert len(chunks) == 1
    assert chunks[0]["text"] == text
    assert chunks[0]["chunk_index"] == 0


def test_long_text_splits_into_multiple_overlapping_chunks():
    words = [f"word{i}" for i in range(100)]
    text = " ".join(words)
    chunks = chunk_text(text, chunk_size=10, overlap_ratio=0.2)

    assert len(chunks) > 1
    # chunk_index is sequential starting at 0
    assert [c["chunk_index"] for c in chunks] == list(range(len(chunks)))

    # every chunk (except possibly the last) has exactly chunk_size tokens
    for c in chunks[:-1]:
        assert len(c["text"].split()) == 10

    # the last chunk reaches the end of the text
    assert chunks[-1]["text"].split()[-1] == "word99"


def test_overlap_ratio_produces_expected_shared_tokens():
    words = [f"w{i}" for i in range(30)]
    text = " ".join(words)
    chunks = chunk_text(text, chunk_size=10, overlap_ratio=0.2)  # overlap=2, stride=8

    first_tokens = chunks[0]["text"].split()
    second_tokens = chunks[1]["text"].split()
    # last 2 tokens of chunk 0 should equal first 2 tokens of chunk 1
    assert first_tokens[-2:] == second_tokens[:2]


def test_preserves_raw_whitespace_within_a_chunk():
    text = "line one\nline   two"
    chunks = chunk_text(text, chunk_size=512, overlap_ratio=0.125)
    assert len(chunks) == 1
    assert chunks[0]["text"] == text


def test_no_overlap_when_ratio_is_zero():
    words = [f"w{i}" for i in range(20)]
    text = " ".join(words)
    chunks = chunk_text(text, chunk_size=10, overlap_ratio=0.0)
    assert len(chunks) == 2
    assert chunks[0]["text"].split()[-1] == "w9"
    assert chunks[1]["text"].split()[0] == "w10"


@pytest.mark.parametrize("chunk_size", [0, -1])
def test_invalid_chunk_size_raises(chunk_size):
    with pytest.raises(ValueError):
        chunk_text("some text", chunk_size=chunk_size)


@pytest.mark.parametrize("overlap_ratio", [-0.1, 1.0, 1.5])
def test_invalid_overlap_ratio_raises(overlap_ratio):
    with pytest.raises(ValueError):
        chunk_text("some text", overlap_ratio=overlap_ratio)
