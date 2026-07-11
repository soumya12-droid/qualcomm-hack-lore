# Lore — Claude Code Context File
> Share this file with your team. When using Claude Code, this file gives the AI full context about the hackathon and project so every teammate gets accurate, consistent help.

---

## The Hackathon

**Event:** Snapdragon Multiverse Hackathon by Qualcomm India
**Location:** Qualcomm Bengaluru Campus
**Date:** July 11–12, 2026
**Duration:** 24 hours to build
**Team size:** 3–5 members

**Official partners:**
- Sarvam AI — Official AI Partner (use their models for Indian language voice support)
- OnePlus — Official Mobile Device Partner (the phone we get is OnePlus, so build for Android)

**Hardware provided to every team:**
- Snapdragon X Series Copilot+ PC (has a dedicated NPU — use it for on-device inference)
- OnePlus mobile device (Android)
- Arduino UNO Q (we are not using this)
- Qualcomm Cloud AI 100 (we are using this)

**Prize we are targeting:** Multi-Device Innovation prize (Ray-Ban Meta AI Glasses for each member)
- Judging criterion: each device must have a distinct, irreplaceable role in the system

---

## The Project — Lore

### One-line pitch
A private, multi-device semantic memory system that indexes everything you personally encounter and makes it instantly queryable from your phone in natural language.

### The problem
We consume hundreds of pieces of information every day — files we write, PDFs we read, articles we browse, text we copy. When we need something specific later, we end up digging through folders, scrolling browser history, or simply forgetting it existed. Nothing remembers it for us privately.

### The solution
Lore runs silently in the background on your PC, indexing everything you work with into a local vector database using semantic embeddings. When you need something, you speak a query into your phone in English or Hindi. Within seconds, your phone surfaces the exact document or article you were looking for — without sending any data to the internet.

### The demo moment (rehearse this until it is perfect)
Someone asks you a question. You take out your phone, speak the query out loud. The exact document or article appears on your phone screen in under 3 seconds. No Google. No internet. Just your own knowledge, privately indexed on your own machine.

### The key line for judges
> "Lore is private by architecture, not by policy — because every computation happens on hardware you own."

---

## Device Architecture

This is the most important thing to understand. Each device has one job. Removing any device breaks the system.

### Device 1 — Snapdragon X Series PC (the brain)
**Job:** Always-on background indexing engine + local API server

- Watches the Windows user folder continuously using `watchdog`
- When files are added or changed: extracts text (PDF, PPT/PPTX, DOCX, XLSX, MD, TXT), chunks it, embeds it with **EmbeddingGemma 300M** running on the NPU via **ONNX Runtime + QNN Execution Provider**, stores vectors in **LanceDB**
- A Chrome browser extension sends web pages you actively read (filtered by 30-second dwell time) into the same pipeline
- Runs a **FastAPI** server on the local network to receive queries from the phone and index requests from the browser extension
- Nothing leaves this machine for indexing/embedding. No internet connection required after setup.

**Why it cannot be replaced by the phone:** The phone cannot run continuous background indexing at this quality. The NPU in the Snapdragon PC is far more powerful than a mobile chip for sustained inference.

### Device 2 — Qualcomm Cloud AI 100 (the intelligence)
**Job:** Query-time reranking and answer generation

- When a query arrives from the phone via the PC's FastAPI server, the Cloud AI 100 takes over
- Receives the query + top-5 candidate embeddings/chunks from LanceDB
- Reranks the candidates semantically and generates a natural language answer with source attribution — not just "here is the file" but "here is what it says and why it is relevant"
- All of this happens within the local private network. Zero external cloud dependency.

**Why it cannot be replaced by a smaller model on the PC:** The embedding model runs continuously on the PC's NPU. Running a large LLM for answer generation simultaneously would bottleneck the system. The Cloud AI 100 handles heavy inference separately without interfering with background indexing.

### Device 3 — Mobile App (the interface)
**Job:** The only thing the user actually touches

- React Native app (Android, OnePlus)
- Mic button → Sarvam AI SDK converts voice to text (supports English and Hindi)
- Sends `{ text, modality }` query to PC's FastAPI endpoint over local WiFi
- Displays results: LLM answer + top 5 file names, locations, and excerpts
- The phone cannot run the indexing or the large LLM — it is purely the access layer

---

## Build Phases

We build this in three phases. Each phase should be independently testable before moving to the next.

### Phase 1 — Indexing (PC)
Goal: a background service that watches the filesystem, extracts + chunks + embeds content, and stores it in LanceDB. No API, no mobile, no Cloud AI 100 yet.

### Phase 2 — Backend API
Goal: FastAPI server exposing `POST /query` and `POST /index`, wired to LanceDB. Cloud AI 100 call can be stubbed/mocked at this stage.

### Phase 3 — Cloud AI 100 Integration
Goal: replace the stub with real reranking + generation on the Cloud AI 100, returning the final answer + top 5 sources to the caller.

---

## Phase 1 — Indexing (Detailed Spec)

### Folder to watch
- The Windows **user folder** (`C:\Users\<username>\`), recursively, via `watchdog`
- Respect reasonable exclusions (e.g. `AppData`, `node_modules`, `.git`, hidden/system folders) to avoid noise — flag this as configurable

### File formats to support
| Extension | Extraction library |
|---|---|
| `.pdf` | PyMuPDF (`fitz`) |
| `.ppt` / `.pptx` | `python-pptx` |
| `.docx` | `python-docx` |
| `.xlsx` | `openpyxl` |
| `.md` | built-in (read as text, strip markdown syntax for embedding, keep raw for storage) |
| `.txt` | built-in |

### Chunking
- Chunk extracted text into overlapping windows (target ~512 tokens, ~10–15% overlap) before embedding
- Preserve structural context per chunk where available: page number (PDF), slide number (PPT), sheet name (XLSX), section/heading (DOCX/MD)

### LanceDB Schema (text table)
```python
{
    "id": str,                # uuid for the record
    "location": str,          # absolute file path or URL
    "title": str,             # filename or page/article title
    "chunk": str,             # raw chunk text
    "embedding": list[float], # EmbeddingGemma 300M vector
    "file_type": str,         # pdf | pptx | docx | xlsx | md | txt | web
    "page": str | None,       # PDF page number, if applicable
    "sheet": str | None,      # XLSX sheet name, if applicable
    "slide": str | None,      # PPTX slide number, if applicable
    "section": str | None,    # DOCX/MD heading/section, if applicable
    "chunk_id": str,          # uuid for this specific chunk
    "chunk_index": int,       # position of chunk within the source document
    "created_at": str,        # ISO 8601 timestamp
    "updated_at": str,        # ISO 8601 timestamp
    "metadata": dict,         # free-form: {"source": "filesystem"|"browser", "dwell_time": ..., "url": ..., etc.}
}
```

### Image table (placeholder — do NOT implement fully yet)
We will index images later using the **jina-clip** model into a **separate LanceDB table** (`images`). For now:
- Create the table schema as a placeholder only (no active pipeline)
- Suggested placeholder schema:
```python
{
    "id": str,
    "location": str,
    "title": str,
    "embedding": list[float],   # jina-clip embedding — NOT wired up yet
    "file_type": str,           # png | jpg | jpeg | etc.
    "created_at": str,
    "updated_at": str,
    "metadata": dict,
}
```
- Leave a clearly marked `# TODO: Phase 4 — image indexing with jina-clip` in the code. Do not build the extraction/embedding pipeline for images yet.

### Embedding model — EmbeddingGemma 300M on NPU
- Model: **EmbeddingGemma 300M** (text embeddings only, for now)
- Runtime: **ONNX Runtime** with the **QNN Execution Provider**, targeting the Snapdragon NPU
- The model must be exported/converted to ONNX and then quantized for QNN before it can run efficiently on-NPU
- Build a **quantization script** (separate from the main indexing pipeline) that:
  - Takes the ONNX EmbeddingGemma 300M model as input
  - Applies QNN-targeted quantization (e.g. static quantization with representative calibration data, INT8 where supported by QNN)
  - Outputs a `.onnx` (or QNN context binary) artifact optimized for NPU execution
  - Is a standalone, re-runnable script (e.g. `scripts/quantize_embedding_model.py`) with clear CLI args for input model path, calibration data path, and output path

### NPU/CPU/GPU Profiling & Fallback
- Build a profiling module that monitors which execution provider is actually being used at inference time (NPU via QNN, CPU, or GPU)
- Responsibilities:
  - Log per-inference latency and which backend served the request
  - Detect if ONNX Runtime silently fell back to CPU (common failure mode when QNN EP can't load/init) and surface a clear warning
  - Provide a simple summary/report function (e.g. % of inferences on NPU vs CPU vs GPU over a session) for debugging and for the judging demo
- Fallback order should be explicit and configurable: **NPU (QNN) → GPU (DirectML, if available) → CPU**

### Phase 1 file structure
```
lore/
├── pc/
│   ├── indexer/
│   │   ├── watcher.py         # watchdog-based filesystem watcher
│   │   ├── extractor.py       # PDF/PPTX/DOCX/XLSX/MD/TXT text extraction
│   │   ├── chunker.py         # text chunking logic
│   │   ├── embedder.py        # EmbeddingGemma 300M via ONNX Runtime + QNN
│   │   ├── vector_store.py    # LanceDB wrapper (text table + image table placeholder)
│   │   └── profiler.py        # NPU/CPU/GPU usage profiling
│   ├── scripts/
│   │   └── quantize_embedding_model.py  # QNN-targeted quantization script
│   └── requirements.txt
```

---

## Phase 2 — Backend API (Detailed Spec)

### Endpoints

#### `POST /query`
**Request body (from mobile app):**
```json
{
  "text": "string",
  "modality": "text"  // or "image" (image modality reserved for future jina-clip support)
}
```

**Behavior:**
1. Embed `text` using the same EmbeddingGemma 300M pipeline used for indexing (if `modality == "text"`)
2. Search LanceDB's text table for the **top 5** nearest matches
3. Send the query + the corresponding top-5 chunks/embeddings to the Cloud AI 100 for reranking + answer generation (Phase 3; can be stubbed in Phase 2)
4. Wait for the Cloud AI 100 response
5. Return the final response to the mobile app

**Response body (to mobile app):**
```json
{
  "answer": "string",              // LLM-generated natural language answer
  "sources": [
    {
      "title": "string",
      "location": "string",        // file path on PC, or URL for web sources
      "excerpt": "string",
      "file_type": "string"
    }
    // ... up to 5 entries
  ]
}
```

#### `POST /index`
**Request body (from browser extension):**
```json
{
  "text": "string",
  "url": "string",
  "title": "string"
}
```

**Behavior:**
1. Map the incoming payload onto the LanceDB text schema:
   - `location` ← `url`
   - `title` ← `title`
   - `chunk` ← chunked `text`
   - `file_type` ← `"web"`
   - `page`, `sheet`, `slide` ← `None`
   - `section` ← `None` (or page heading, if extracted)
   - `metadata` ← `{"source": "browser", "url": url}`
2. Embed each chunk using the same EmbeddingGemma 300M model used for filesystem indexing (shared embedder module — do not duplicate)
3. Insert records into LanceDB
4. Return a simple success/failure acknowledgment to the extension

### Logging
- Add structured logging across the backend (e.g. Python `logging` module configured with a rotating file handler + console handler)
- Log at minimum: incoming requests (endpoint, payload size, timestamp), embedding time, LanceDB search latency, Cloud AI 100 round-trip latency, errors/exceptions with stack traces
- Use consistent log levels: `DEBUG` for internals (chunk counts, vector dims), `INFO` for request lifecycle, `WARNING` for fallbacks (e.g. NPU→CPU), `ERROR` for failures
- Keep logs structured enough to be greppable/debuggable under demo pressure (include request IDs)

### Phase 2 file structure
```
lore/
├── pc/
│   ├── api/
│   │   ├── main.py            # FastAPI app, route registration
│   │   ├── routes_query.py    # POST /query handler
│   │   ├── routes_index.py    # POST /index handler
│   │   ├── schemas.py         # Pydantic request/response models
│   │   ├── logging_config.py  # logging setup
│   │   └── cloud_client.py    # client stub for Cloud AI 100 (Phase 2 stub, Phase 3 real)
```

---

## Phase 3 — Cloud AI 100 Integration (Detailed Spec)

- Replace the stub in `cloud_client.py` with a real client that talks to the Cloud AI 100 over the local network
- Interface with the Cloud AI 100 via the **Qualcomm AI SDK**
- Load **LLaMA 3 8B** or **Phi-3 mini** on-premises on the Cloud AI 100
- Input: original query text + top-5 chunks/embeddings from LanceDB (passed from the PC's `/query` handler)
- Processing:
  1. Semantic reranker reorders the top-5 candidates by relevance to the query
  2. LLM generates a natural language answer grounded in the reranked chunks, with source attribution
- Output back to PC: `{ "answer": str, "ranked_sources": [...] }`
- The PC's `/query` handler assembles this into the final mobile-facing response (answer + top 5 file names/locations)
- Target latency: reranking + generation adds ~1–2 seconds on top of the <500ms LanceDB search, for an end-to-end target of under 3 seconds

### Phase 3 file structure
```
lore/
├── cloud/
│   ├── inference.py         # Cloud AI 100 interface via Qualcomm AI SDK
│   ├── reranker.py          # Semantic reranking logic
│   └── requirements.txt
```

---

## Full Tech Stack

### Mobile (React Native — Android)
| Library | Purpose |
|---|---|
| React Native | Cross-platform mobile UI |
| Sarvam AI SDK | Voice input — English and Hindi |
| Axios | HTTP calls to PC's local API |

### PC — Indexing Engine (Python)
| Library | Purpose |
|---|---|
| watchdog | Monitor Windows user folder for changes |
| PyMuPDF (fitz) | Extract text from PDFs |
| python-docx | Extract text from Word documents |
| python-pptx | Extract text from PowerPoint files |
| openpyxl | Extract text/data from Excel files |
| onnxruntime + onnxruntime-qnn | Run EmbeddingGemma 300M on Snapdragon NPU |
| EmbeddingGemma 300M | Text embedding model |
| jina-clip (placeholder only) | Future image embedding model — not wired up yet |
| LanceDB | Local vector database — text table + image table placeholder |
| FastAPI | Local REST API server — receives queries/index requests |
| uvicorn | ASGI server to run FastAPI |

### PC — Browser Extension (JavaScript)
| Component | Purpose |
|---|---|
| Chrome Extension Manifest V3 | Extension scaffold |
| content_script.js | Detects 30-second dwell time on pages |
| background.js | Service worker — POSTs `{text, url, title}` to PC's `/index` endpoint |

### Cloud AI 100 (Python + Qualcomm SDK)
| Component | Purpose |
|---|---|
| Qualcomm AI SDK | Interface with Cloud AI 100 hardware |
| LLaMA 3 8B or Phi-3 mini | Large language model for answer generation |
| Semantic reranker | Reorders LanceDB results by relevance to query |

### Tooling
| Tool | Purpose |
|---|---|
| Python `logging` | Structured backend logging |
| ONNX Runtime QNN quantization tooling | NPU-targeted model quantization |

---

## Data Flow (step by step)

```
[User saves a file / reads a web page for 30+ seconds]
        ↓
[PC: watchdog detects change OR browser extension captures page]
        ↓
[PC: text extraction — PyMuPDF / python-pptx / python-docx / openpyxl / raw text]
        ↓
[PC: chunking]
        ↓
[PC: EmbeddingGemma 300M via ONNX Runtime + QNN on NPU (CPU/GPU fallback if needed) → vector]
        ↓
[PC: vector + metadata stored in LanceDB, per schema above]
        ↓  (this happens continuously in background)

[User speaks query into phone]
        ↓
[Mobile: Sarvam AI converts voice to text]
        ↓
[Mobile: Axios sends POST /query {text, modality} to PC's FastAPI server over local WiFi]
        ↓
[PC: FastAPI embeds query (EmbeddingGemma 300M) → searches LanceDB → top 5 matches + embeddings]
        ↓
[Cloud AI 100: receives query + top 5 chunks/embeddings via local network]
        ↓
[Cloud AI 100: reranks + LLaMA 3 / Phi-3 generates natural language answer with source attribution]
        ↓
[PC: assembles { answer, sources[5] } and sends back to phone]
        ↓
[Mobile: displays answer + file name, location, excerpt for each source]
```

---

## Critical Setup Notes

### Local network
- The phone and PC must be on the same WiFi network
- Venue WiFi sometimes blocks device-to-device communication
- **First thing on day one:** set up a mobile hotspot from the PC, connect the phone to it
- Hardcode the PC's local IP in the mobile app for the hackathon (no time for discovery protocols)

### ONNX Runtime + QNN on Snapdragon NPU
- After setting up `onnxruntime-qnn`, verify the QNN Execution Provider is actually being used, not silently falling back to CPU
- Use the profiling module (Phase 1) to confirm NPU usage during embedding
- If CPU usage spikes instead of NPU, check that the quantized model is QNN-compatible and that the QNN EP initialized correctly

### Demo files
- Load at least 50 real files before the demo (research papers, articles, notes)
- Prepare 10 specific queries you know will return great results
- Rehearse the exact demo flow at least 10 times
- Have a backup plan if WiFi fails: pre-run a query and screenshot the result

---

## Code Documentation Standards

To keep debugging fast under hackathon time pressure:
- Every module gets a top-of-file docstring: what it does, its inputs/outputs, and which phase it belongs to
- Every function gets a docstring with args, return type, and any side effects (e.g. "writes to LanceDB", "calls Cloud AI 100 over network")
- Inline comments should explain **why**, not just what, especially around: NPU/CPU/GPU fallback logic, chunking boundaries, and the Cloud AI 100 request/response contract
- Mark all placeholder/future code clearly, e.g. `# TODO: Phase 4 — image indexing with jina-clip`, so no one accidentally treats it as functional
- Log statements should double as inline documentation of the control flow for anyone reading logs during a live demo failure

---

## What judges will ask — and how to answer

**Q: Why not just use ChatGPT or Notion AI?**
A: Those send your data to external servers. Lore never does. Every computation — indexing and search — happens on hardware you own. For medical records, personal notes, confidential work documents, that is not a minor detail. It is the whole point.

**Q: Why do you need three devices? Can this not run on just the PC?**
A: The PC indexes in the background and the Cloud AI 100 handles query-time inference simultaneously. Running a large LLM for answer generation on the same machine that is continuously embedding new content would create a bottleneck — the indexing would stall every time you search. The phone is always with you; the PC is not. Each device is doing something the others cannot.

**Q: How does this scale beyond one person?**
A: On-device means we distribute the model like software, not the computation like a service. Every Snapdragon device becomes its own node. No server costs, no per-query charges, no data liability. A team, a clinic, a hospital — each runs their own instance. The Cloud AI 100 model handles private enterprise deployments inside their own network.

**Q: What is the latency?**
A: Embedding a query and searching LanceDB takes under 500ms. The Cloud AI 100 inference adds 1–2 seconds. End-to-end from voice query to result on screen: under 3 seconds. That is our target.

**Q: Why EmbeddingGemma 300M and not a bigger embedding model?**
A: It needs to run continuously in the background on the NPU without draining the device or competing with other work. A 300M model quantized for QNN keeps embedding fast and cheap enough to run on every file save and every article read, all day, without the user noticing.

---

## Useful commands

```bash
# Install Python dependencies (PC indexing + API)
pip install watchdog pymupdf python-docx python-pptx openpyxl lancedb fastapi uvicorn onnxruntime onnxruntime-qnn

# Run the quantization script (QNN-targeted)
python pc/scripts/quantize_embedding_model.py --input model.onnx --calibration-data ./calib_data --output model_qnn_int8.onnx

# Run FastAPI server
uvicorn pc.api.main:app --host 0.0.0.0 --port 8000 --reload

# Test query endpoint
curl -X POST http://localhost:8000/query -H "Content-Type: application/json" -d '{"text": "neural embeddings research", "modality": "text"}'

# Test index endpoint (simulating browser extension)
curl -X POST http://localhost:8000/index -H "Content-Type: application/json" -d '{"text": "page content...", "url": "https://example.com/article", "title": "Article Title"}'

# Check PC local IP (for hardcoding in mobile app)
ip addr show   # Linux
ipconfig       # Windows
```

---

## File structure (full project, all phases)

```
lore/
├── pc/
│   ├── indexer/
│   │   ├── watcher.py          # watchdog-based filesystem watcher (Windows user folder)
│   │   ├── extractor.py        # PDF/PPTX/DOCX/XLSX/MD/TXT text extraction
│   │   ├── chunker.py          # text chunking logic
│   │   ├── embedder.py         # EmbeddingGemma 300M via ONNX Runtime + QNN
│   │   ├── vector_store.py     # LanceDB wrapper (text table + image table placeholder)
│   │   └── profiler.py         # NPU/CPU/GPU usage profiling
│   ├── api/
│   │   ├── main.py             # FastAPI app, route registration
│   │   ├── routes_query.py     # POST /query handler
│   │   ├── routes_index.py     # POST /index handler
│   │   ├── schemas.py          # Pydantic request/response models
│   │   ├── logging_config.py   # logging setup
│   │   └── cloud_client.py     # Cloud AI 100 client (stub in Phase 2, real in Phase 3)
│   ├── scripts/
│   │   └── quantize_embedding_model.py  # QNN-targeted quantization script
│   └── requirements.txt
├── cloud/
│   ├── inference.py            # Cloud AI 100 interface via Qualcomm AI SDK
│   ├── reranker.py             # Semantic reranking logic
│   └── requirements.txt
├── extension/
│   ├── manifest.json
│   ├── content_script.js       # Dwell time detection
│   └── background.js           # Page capture + POST {text, url, title} to PC's /index endpoint
└── mobile/
    ├── App.js
    ├── screens/
    │   └── QueryScreen.js       # Mic button + results display
    └── package.json
```

---

## Context for Claude Code

When asking Claude Code for help on this project, reference this file for context and specify which phase you're working on. Useful prompts:

- *"Using CLAUDE.md, we're in Phase 1. Write `watcher.py` that watches the Windows user folder recursively with watchdog and calls the extractor on new/changed files, respecting the exclusion list."*
- *"Using CLAUDE.md, write `embedder.py` that loads EmbeddingGemma 300M via ONNX Runtime with the QNN Execution Provider, falls back to CPU/GPU if QNN init fails, and logs which backend was used."*
- *"Using CLAUDE.md, write `scripts/quantize_embedding_model.py` that quantizes the EmbeddingGemma 300M ONNX model for QNN, taking input/output/calibration paths as CLI args."*
- *"Using CLAUDE.md, write `vector_store.py` with the LanceDB text table per the schema, plus a placeholder `images` table creation function (no embedding pipeline yet)."*
- *"Using CLAUDE.md, we're in Phase 2. Write the FastAPI `/query` endpoint that embeds the incoming text, searches LanceDB for the top 5 matches, and calls a stubbed `cloud_client.rerank_and_generate()`."*
- *"Using CLAUDE.md, write the FastAPI `/index` endpoint that maps `{text, url, title}` from the browser extension onto the LanceDB schema and embeds it with the shared embedder module."*
- *"Using CLAUDE.md, write `logging_config.py` with a rotating file handler and console handler, and show how to use it in the query/index routes."*
- *"Using CLAUDE.md, we're in Phase 3. Write `cloud/inference.py` that loads Phi-3 mini on the Cloud AI 100 via the Qualcomm AI SDK and implements rerank + generate given a query and top-5 chunks."*
- *"Using CLAUDE.md, write the Chrome extension `content_script.js` that detects 30-second dwell time and sends `{text, url, title}` to the PC's `/index` endpoint."*
- *"Using CLAUDE.md, write the React Native `QueryScreen.js` with a mic button using the Sarvam AI SDK, sending `{text, modality: "text"}` to `/query` and rendering the answer + top 5 sources."*