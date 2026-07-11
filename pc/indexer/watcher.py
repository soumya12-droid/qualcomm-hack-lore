"""Phase 1 — watchdog-based filesystem watcher: on file create/modify events
for supported extensions, runs extractor -> chunker -> embedder ->
vector_store to index the file, skipping configured exclusions.

Input: a root directory to watch, plus a wired Embedder and VectorStore.
Output: none directly; indexed chunk rows land in the given VectorStore.
Side effects: starts a watchdog Observer thread; reads files from disk;
writes to LanceDB via VectorStore.upsert_chunks(); logs pipeline progress.
"""

import logging
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from pc.indexer import chunker, extractor
from pc.indexer.extractor import UnsupportedFileTypeError

logger = logging.getLogger(__name__)

# Configurable — flagged per CLAUDE.md as "reasonable exclusions... flag
# this as configurable". Callers can override via excluded_dir_names.
DEFAULT_EXCLUDED_DIR_NAMES = frozenset({
    "AppData",
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "$Recycle.Bin",
    "System Volume Information",
})


def is_excluded(path, root, excluded_dir_names=DEFAULT_EXCLUDED_DIR_NAMES):
    """True if any directory component between `root` and `path` is a
    configured exclusion or a hidden directory (name starting with '.')."""
    path = Path(path)
    root = Path(root)
    try:
        relative_parts = path.relative_to(root).parts
    except ValueError:
        relative_parts = path.parts
    for part in relative_parts[:-1]:  # directories only, not the filename itself
        if part in excluded_dir_names or part.startswith("."):
            return True
    return False


def index_file(file_path, embedder, vector_store, source="filesystem"):
    """Run extractor -> chunker -> embedder -> vector_store for one file.

    Args:
        file_path: path to the file to index.
        embedder: an object exposing embed(list[str]) -> list[list[float]].
        vector_store: a VectorStore to upsert the resulting chunk rows into.
        source: tagged into each row's metadata (e.g. "filesystem", "browser").

    Returns:
        Number of chunk rows written (0 if the file type is unsupported,
        extraction fails, or yields no content).
    Side effects: reads file_path from disk; calls embedder.embed(); writes
        to vector_store; logs progress/errors.
    """
    file_path = Path(file_path)
    file_type = extractor.file_type_for(file_path)
    if file_type is None:
        logger.debug("Skipping unsupported file type: %s", file_path)
        return 0

    try:
        segments = extractor.extract(file_path)
    except UnsupportedFileTypeError:
        return 0
    except Exception:
        logger.exception("Extraction failed for %s", file_path)
        return 0

    if not segments:
        return 0

    records = []
    for segment in segments:
        for chunk in chunker.chunk_text(segment["text"]):
            records.append({
                "location": str(file_path),
                "title": file_path.name,
                "chunk": chunk["text"],
                "file_type": file_type,
                "page": segment.get("page"),
                "sheet": segment.get("sheet"),
                "slide": segment.get("slide"),
                "section": segment.get("section"),
                "chunk_index": chunk["chunk_index"],
                "metadata": {"source": source},
            })

    if not records:
        return 0

    # Strip Markdown syntax for embedding-time text only; the stored "chunk"
    # field stays raw, per CLAUDE.md's ".md" extraction contract.
    texts_to_embed = [
        extractor.strip_markdown_syntax(record["chunk"]) if file_type == "md" else record["chunk"]
        for record in records
    ]
    embeddings = embedder.embed(texts_to_embed)
    for record, embedding in zip(records, embeddings):
        record["embedding"] = embedding

    vector_store.upsert_chunks(records)
    logger.info("Indexed %d chunk(s) from %s", len(records), file_path)
    return len(records)


class _IndexingEventHandler(FileSystemEventHandler):
    def __init__(self, root, embedder, vector_store, excluded_dir_names):
        self.root = Path(root)
        self.embedder = embedder
        self.vector_store = vector_store
        self.excluded_dir_names = excluded_dir_names

    def _maybe_index(self, path):
        path = Path(path)
        if path.is_dir():
            return
        if is_excluded(path, self.root, self.excluded_dir_names):
            logger.debug("Excluded path, skipping: %s", path)
            return
        index_file(path, self.embedder, self.vector_store)

    def on_created(self, event):
        if not event.is_directory:
            self._maybe_index(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._maybe_index(event.src_path)


class Watcher:
    """Recursively watches `root` for created/modified files, indexing
    supported, non-excluded files through the extractor->chunker->embedder->
    vector_store pipeline."""

    def __init__(self, root, embedder, vector_store, excluded_dir_names=DEFAULT_EXCLUDED_DIR_NAMES):
        self.root = Path(root)
        self.handler = _IndexingEventHandler(self.root, embedder, vector_store, excluded_dir_names)
        self.observer = Observer()

    def start(self):
        """Start watching self.root recursively. Side effects: spawns a watchdog observer thread."""
        self.observer.schedule(self.handler, str(self.root), recursive=True)
        self.observer.start()
        logger.info("Watching %s for changes", self.root)

    def stop(self):
        """Stop the observer thread and block until it exits."""
        self.observer.stop()
        self.observer.join()
