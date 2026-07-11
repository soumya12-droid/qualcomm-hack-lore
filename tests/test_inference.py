import pytest

from cloud.inference import CloudAI100Client, build_prompt, generate_answer


class FakeClient:
    def __init__(self, answer="a fake answer"):
        self.answer = answer
        self.received_prompt = None

    def generate(self, prompt):
        self.received_prompt = prompt
        return self.answer


def test_build_prompt_includes_query_and_numbered_sources():
    chunks = [
        {"title": "notes.txt", "chunk": "the hackathon starts July 11"},
        {"title": "paper.pdf", "chunk": "neural embeddings research"},
    ]
    prompt = build_prompt("when does it start", chunks)

    assert "when does it start" in prompt
    assert "[1] notes.txt: the hackathon starts July 11" in prompt
    assert "[2] paper.pdf: neural embeddings research" in prompt
    assert prompt.strip().endswith("Answer:")


def test_build_prompt_instructs_citation_and_grounding():
    prompt = build_prompt("query", [{"title": "a", "chunk": "b"}])
    assert "cite" in prompt.lower()
    assert "only" in prompt.lower()


def test_build_prompt_with_no_chunks_notes_no_sources():
    prompt = build_prompt("query", [])
    assert "(no sources provided)" in prompt
    assert "query" in prompt


def test_build_prompt_truncates_long_chunk_text():
    long_text = "word " * 200  # far more than MAX_CHUNK_CHARS
    prompt = build_prompt("query", [{"title": "long", "chunk": long_text}])
    assert "..." in prompt
    assert len(prompt) < len(long_text) + 500


def test_build_prompt_handles_missing_title():
    prompt = build_prompt("query", [{"chunk": "content with no title"}])
    assert "untitled source" in prompt


def test_cloud_ai100_client_raises_not_implemented_on_construction():
    with pytest.raises(NotImplementedError, match="Qualcomm AI SDK"):
        CloudAI100Client()


def test_cloud_ai100_client_error_message_includes_model_and_device():
    with pytest.raises(NotImplementedError, match="phi-3-mini"):
        CloudAI100Client(model_name="phi-3-mini", device_id=2)


def test_generate_answer_calls_client_with_built_prompt():
    fake = FakeClient(answer="hackathon starts July 11, per notes.txt")
    chunks = [{"title": "notes.txt", "chunk": "the hackathon starts July 11"}]

    answer = generate_answer("when does it start", chunks, fake)

    assert answer == "hackathon starts July 11, per notes.txt"
    assert fake.received_prompt == build_prompt("when does it start", chunks)


def test_generate_answer_propagates_client_exceptions():
    class FailingClient:
        def generate(self, prompt):
            raise RuntimeError("hardware unavailable")

    with pytest.raises(RuntimeError, match="hardware unavailable"):
        generate_answer("query", [], FailingClient())
