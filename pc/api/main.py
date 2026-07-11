"""Phase 2 — FastAPI app assembly: builds the shared Embedder/VectorStore
into app.state at startup (from env-configured paths), configures
structured logging, and registers the API routers.

Input: environment variables EMBEDDING_MODEL_PATH, LANCEDB_PATH,
EMBEDDING_DIM, LOG_FILE (all have local-dev defaults below).
Output: the `app` FastAPI instance — run via `uvicorn pc.api.main:app`.
Side effects: on startup, loads the embedding model file, connects to
LanceDB, and configures logging (rotating file handler under LOG_FILE).
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from pc.api import routes_index, routes_query
from pc.api.logging_config import configure_logging
from pc.indexer.embedder import Embedder
from pc.indexer.vector_store import VectorStore

DEFAULT_EMBEDDING_MODEL_PATH = "models/embedding_gemma_300m_qnn_int8.onnx"
DEFAULT_LANCEDB_PATH = "lancedb"
DEFAULT_LOG_FILE = "lore.log"
DEFAULT_EMBEDDING_DIM = 768  # EmbeddingGemma 300M's output dimension


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Side effects: configures logging; loads the embedding model
    (onnxruntime.InferenceSession) and opens the LanceDB tables, storing
    both on app.state for the dependency providers in dependencies.py."""
    configure_logging(log_file=os.environ.get("LOG_FILE", DEFAULT_LOG_FILE))

    model_path = os.environ.get("EMBEDDING_MODEL_PATH", DEFAULT_EMBEDDING_MODEL_PATH)
    lancedb_path = os.environ.get("LANCEDB_PATH", DEFAULT_LANCEDB_PATH)
    embedding_dim = int(os.environ.get("EMBEDDING_DIM", DEFAULT_EMBEDDING_DIM))

    app.state.embedder = Embedder(model_path)
    app.state.vector_store = VectorStore(lancedb_path, embedding_dim=embedding_dim)
    yield


app = FastAPI(title="Lore", lifespan=lifespan)
app.include_router(routes_query.router)
app.include_router(routes_index.router)


@app.get("/health")
def health():
    return {"status": "ok"}
