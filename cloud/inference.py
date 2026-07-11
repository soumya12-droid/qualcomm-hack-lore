"""Phase 3 — Cloud AI 100 interface via the Qualcomm AI SDK: builds a
grounded prompt from the query + reranked chunks and runs LLM generation
(LLaMA 3 8B / Phi-3 mini, per CLAUDE.md) on the Cloud AI 100 accelerator.

NOT WIRED TO REAL HARDWARE: this sandbox has no Cloud AI 100 device and no
Qualcomm AI SDK, and there is no verified documentation available here for
that SDK's actual package/class/method names — it is proprietary,
hardware-specific software. CloudAI100Client's session loading and
generation calls are intentionally left as NotImplementedError stubs
rather than guessed-at SDK calls; wire them up on-site at the hackathon
using the real Qualcomm AI SDK docs. Everything else in this module
(prompt construction, the generate_answer orchestration) is real.

Input: query text + reranked chunk rows (from cloud.reranker.rerank()).
Output: build_prompt() -> str; generate_answer() -> str (the model's answer).
Side effects: CloudAI100Client.__init__()/generate() will, once wired,
talk to the Cloud AI 100 accelerator. build_prompt() and generate_answer()
themselves have no side effects beyond calling the provided client.
"""

MAX_CHUNK_CHARS = 500


def build_prompt(query, reranked_chunks):
    """Build a grounded prompt instructing the model to answer only from
    the given chunks and cite sources by title.

    Args:
        query: the user's original query text.
        reranked_chunks: chunk row dicts (title, chunk, location, ...),
            nearest-first per cloud.reranker.rerank().

    Returns:
        A prompt string listing each source (numbered, titled, excerpted)
        followed by instructions to answer only from those sources and
        cite them by title.
    """
    source_lines = []
    for index, chunk in enumerate(reranked_chunks, start=1):
        title = chunk.get("title") or "untitled source"
        text = (chunk.get("chunk") or "").strip()
        if len(text) > MAX_CHUNK_CHARS:
            text = text[:MAX_CHUNK_CHARS].rstrip() + "..."
        source_lines.append(f"[{index}] {title}: {text}")
    sources_block = "\n".join(source_lines) if source_lines else "(no sources provided)"

    return (
        "You are Lore, a private on-device assistant. Answer the user's "
        "question using ONLY the sources below. Cite each source you use "
        "by its title. If the sources don't contain the answer, say so.\n\n"
        f"Sources:\n{sources_block}\n\n"
        f"Question: {query}\n"
        "Answer:"
    )


class CloudAI100Client:
    """Real hardware interface skeleton for the Cloud AI 100 accelerator.

    TODO (Phase 3, on-site): replace _load_session() and generate() with
    real calls into the Qualcomm AI SDK, loading LLaMA 3 8B or Phi-3 mini
    per CLAUDE.md's spec. Left unimplemented here because this sandbox has
    neither the hardware nor the SDK, and no verified API reference was
    available to write against — guessing at the API would risk shipping
    code that only reveals it's wrong at demo time.
    """

    def __init__(self, model_name="phi-3-mini", device_id=0):
        self.model_name = model_name
        self.device_id = device_id
        self._session = self._load_session()

    def _load_session(self):
        raise NotImplementedError(
            "CloudAI100Client is not wired to real hardware yet. Replace "
            "_load_session() with a real Qualcomm AI SDK session for the "
            f"Cloud AI 100 accelerator (model={self.model_name!r}, "
            f"device_id={self.device_id!r}), per CLAUDE.md's Phase 3 spec."
        )

    def generate(self, prompt):
        raise NotImplementedError(
            "CloudAI100Client is not wired to real hardware yet. Replace "
            "generate() with a real Qualcomm AI SDK inference call."
        )


def generate_answer(query, reranked_chunks, client):
    """Generate a grounded answer for `query` using `reranked_chunks` as
    context, via `client.generate()`.

    Args:
        query: the user's original query text.
        reranked_chunks: chunk row dicts, nearest-first.
        client: any object exposing generate(prompt: str) -> str (a real
            CloudAI100Client, or a test double).

    Returns:
        The model's answer text (client.generate()'s return value).
    Side effects: whatever client.generate() does (a real hardware call,
        once CloudAI100Client is wired up).
    """
    prompt = build_prompt(query, reranked_chunks)
    return client.generate(prompt)
