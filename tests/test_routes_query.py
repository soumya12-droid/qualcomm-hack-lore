import numpy as np
import onnx
import pytest
from onnx import TensorProto, helper
from starlette.testclient import TestClient

INPUT_DIM = 16
EMBEDDING_DIM = 8


def _build_toy_onnx_model(path, input_dim=INPUT_DIM, embedding_dim=EMBEDDING_DIM):
    weight = np.random.RandomState(0).randn(input_dim, embedding_dim).astype(np.float32)
    weight_initializer = helper.make_tensor(
        "weight", TensorProto.FLOAT, weight.shape, weight.flatten().tolist()
    )
    input_tensor = helper.make_tensor_value_info("input", TensorProto.FLOAT, [None, input_dim])
    output_tensor = helper.make_tensor_value_info("embedding", TensorProto.FLOAT, [None, embedding_dim])
    node = helper.make_node("MatMul", inputs=["input", "weight"], outputs=["embedding"])
    graph = helper.make_graph(
        [node], "toy_embedder", [input_tensor], [output_tensor], initializer=[weight_initializer]
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
    onnx.checker.check_model(model)
    onnx.save(model, str(path))
    return path


@pytest.fixture
def client(tmp_path, monkeypatch):
    model_path = _build_toy_onnx_model(tmp_path / "toy.onnx")
    monkeypatch.setenv("EMBEDDING_MODEL_PATH", str(model_path))
    monkeypatch.setenv("LANCEDB_PATH", str(tmp_path / "lancedb"))
    monkeypatch.setenv("EMBEDDING_DIM", str(EMBEDDING_DIM))
    monkeypatch.setenv("LOG_FILE", str(tmp_path / "lore.log"))

    from pc.api.main import app

    with TestClient(app) as test_client:
        # pre-seed the vector store with a few chunk rows to search against
        vector_store = app.state.vector_store
        vector_store.upsert_chunks([
            {
                "location": "/home/user/notes.txt",
                "title": "notes.txt",
                "chunk": "The Snapdragon Multiverse Hackathon runs July 11-12.",
                "embedding": [1.0] + [0.0] * (EMBEDDING_DIM - 1),
                "file_type": "txt",
                "chunk_index": 0,
                "metadata": {"source": "filesystem"},
            },
            {
                "location": "/home/user/paper.pdf",
                "title": "paper.pdf",
                "chunk": "Neural embeddings research paper abstract.",
                "embedding": [0.0, 1.0] + [0.0] * (EMBEDDING_DIM - 2),
                "file_type": "pdf",
                "page": "1",
                "chunk_index": 0,
                "metadata": {"source": "filesystem"},
            },
        ])
        yield test_client


def test_query_returns_answer_and_sources(client):
    response = client.post("/query", json={"text": "when is the hackathon"})
    assert response.status_code == 200

    body = response.json()
    assert "answer" in body
    assert isinstance(body["answer"], str) and body["answer"]
    assert "sources" in body
    assert 1 <= len(body["sources"]) <= 5


def test_query_source_shape_matches_schema(client):
    response = client.post("/query", json={"text": "hackathon dates"})
    body = response.json()

    for source in body["sources"]:
        assert set(source.keys()) == {"title", "location", "excerpt", "file_type"}


def test_query_defaults_modality_to_text(client):
    response = client.post("/query", json={"text": "no modality specified"})
    assert response.status_code == 200


def test_query_rejects_missing_text(client):
    response = client.post("/query", json={"modality": "text"})
    assert response.status_code == 422


def test_query_rejects_invalid_modality(client):
    response = client.post("/query", json={"text": "hi", "modality": "audio"})
    assert response.status_code == 422


def test_query_answer_references_top_ranked_source(client):
    # cloud_client's stub always references the top candidate's title in the answer
    response = client.post("/query", json={"text": "hackathon dates"})
    body = response.json()
    assert body["sources"][0]["title"] in body["answer"]
