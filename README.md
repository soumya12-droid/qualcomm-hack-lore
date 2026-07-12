# Lore

**A private, multi-device semantic memory system.** Lore indexes everything you personally read and write — files, PDFs, web pages, even text baked into images — into a local vector database on your own machine. Ask it a question by voice or text from your phone, and it answers in natural language with the exact source, in seconds, without a single byte leaving hardware you own.

Built for the **Snapdragon Multiverse Hackathon** (Qualcomm India, Bengaluru — July 11–12, 2026). See [`CLAUDE.md`](CLAUDE.md) for the full project brief, and [`SNAPDRAGON_PC_SETUP.md`](SNAPDRAGON_PC_SETUP.md) for a from-scratch setup walkthrough on the real Snapdragon X ARM64 hardware.

> "Lore is private by architecture, not by policy — every computation happens on hardware you own."

---

## Table of contents

- [Architecture](#architecture)
- [Repository layout](#repository-layout)
- [Getting started](#getting-started)
  - [1. Backend (PC indexer + API)](#1-backend-pc-indexer--api)
  - [2. Cloud AI 100 (Imagine SDK)](#2-cloud-ai-100-imagine-sdk)
  - [3. Mobile app](#3-mobile-app)
  - [4. Browser extension](#4-browser-extension)
- [Configuration reference](#configuration-reference)
- [Running the tests](#running-the-tests)
- [Current status](#current-status)
- [Tech stack](#tech-stack)
- [Acknowledgments](#acknowledgments)

---

## Architecture

Three devices, three distinct jobs. Removing any one of them breaks the system.

```
┌─────────────────────┐        ┌──────────────────────┐        ┌────────────────────────┐
│   Mobile app         │        │  Snapdragon X PC       │        │  Qualcomm Cloud AI 100  │
│   (Kotlin/Compose)   │        │  (the brain)            │        │  (the intelligence)     │
│                      │  WiFi  │                          │  LAN   │                          │
│  Voice/text query ───┼───────►│  FastAPI  /query          │───────►│  Rerank + generate       │
│  Sarvam AI STT       │        │  FastAPI  /index           │       │  via Cirrascale's        │
│  Answer + sources ◄──┼────────│  watchdog file watcher      │◄──────│  Imagine SDK             │
│                      │        │  EmbeddingGemma on NPU       │       │  (Llama-3.1-8B, etc.)    │
│                      │        │  (ONNX Runtime + QNN EP)     │       │                          │
│                      │        │  LanceDB (vector store)      │       │                          │
└─────────────────────┘        └──────────────────────────────┘       └──────────────────────────┘
                                            ▲
                                            │ POST /index
                                 ┌──────────┴───────────┐
                                 │  Browser extension     │
                                 │  (MV3, captures pages,  │
                                 │  PDFs, and images you   │
                                 │  actually read)         │
                                 └──────────────────────────┘
```

- **PC** — always-on background indexer (`pc/indexer/`) + local FastAPI server (`pc/api/`). Watches the filesystem, extracts and chunks text, embeds it with EmbeddingGemma 300M on the NPU via ONNX Runtime's QNN execution provider, and stores vectors in LanceDB. Nothing leaves this machine during indexing.
- **Cloud AI 100** — query-time reranking and answer generation (`cloud/`), reached over the local network via Cirrascale's Imagine SDK. Keeps heavy LLM inference off the PC so it never stalls background indexing.
- **Mobile app** — the only thing the user touches (`mobile/`). Records a voice query, transcribes it via Sarvam AI, sends it to the PC over WiFi, and renders the answer + sources.
- **Browser extension** — a Manifest V3 extension (`extension/`) that feeds actively-read web pages, PDFs, and OCR'd image text into the same indexing pipeline via `POST /index`.

## Repository layout

```
lore/
├── pc/                      Python — indexing engine + FastAPI backend
│   ├── indexer/             watcher, extractor, chunker, embedder, vector_store, profiler
│   ├── api/                 FastAPI app, routes, schemas, logging, cloud_client
│   └── scripts/             CLI entry points + NPU quantization/export tooling
├── cloud/                   Cloud AI 100 client: reranking + LLM generation via Imagine SDK
├── mobile/                  Native Android app (Kotlin + Jetpack Compose)
├── extension/               Chrome MV3 extension (text/PDF/image capture)
├── tests/                   Python test suite (pytest)
├── scratch/                 One-off NPU/ONNX debugging scripts (not part of the pipeline)
├── CLAUDE.md                Full project brief and phase-by-phase spec
├── SNAPDRAGON_PC_SETUP.md   From-scratch setup guide for the real ARM64 hardware
└── README.md                You are here
```

## Getting started

### 1. Backend (PC indexer + API)

Requires **Python 3.9+**. For the real deployment target — an **ARM64 Snapdragon laptop** with `onnxruntime-qnn` — follow [`SNAPDRAGON_PC_SETUP.md`](SNAPDRAGON_PC_SETUP.md) instead; it covers the ARM64-native Python requirement, the QNN wheel install, and NPU verification in detail. The steps below are the fast path for any other machine (Linux/macOS/x64 Windows), useful for development and everything except real on-NPU embeddings.

```bash
python -m venv .venv
source .venv/bin/activate          # .venv\Scripts\Activate.ps1 on Windows
pip install -r pc/requirements-dev.txt
```

Run the test suite as a sanity check:

```bash
pytest
```

Start the API server:

```bash
export EMBEDDING_MODEL_PATH=models/smoke.onnx   # see below to generate a smoke-test model
export LANCEDB_PATH=lancedb
export EMBEDDING_DIM=768
export LOG_FILE=lore.log
uvicorn pc.api.main:app --host 0.0.0.0 --port 8000
```

No real EmbeddingGemma export handy yet? Generate a tiny synthetic model to validate the pipeline end-to-end (session creation, provider selection, LanceDB wiring — not real semantic search):

```bash
python pc/scripts/build_smoke_model.py --output models/smoke.onnx
```

Run the background filesystem watcher separately:

```bash
python pc/scripts/run_indexer.py
```

Verify it's alive:

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/query -H "Content-Type: application/json" \
  -d '{"text": "neural embeddings research", "modality": "text"}'
```

### 2. Cloud AI 100 (Imagine SDK)

`/query` falls back to a deterministic templated answer until this is configured — `IMAGINE_API_KEY` is the entire integration surface, no code changes required.

1. Get an API key at [aisuite.cirrascale.com/api-keys](https://aisuite.cirrascale.com/api-keys), and download the Imagine SDK 0.4.2 wheel from [aisuite.cirrascale.com/sdk/install.html](https://aisuite.cirrascale.com/sdk/install.html).
2. Install it and set environment variables:

   ```bash
   pip install imagine_sdk-0.4.2-py3-none-any.whl
   export IMAGINE_API_KEY=your-api-key-here
   export IMAGINE_MODEL_NAME=Llama-3.1-8B   # whichever model your account has on Cloud AI 100
   ```
3. Restart `uvicorn`. Check `lore.log` for `Cloud AI 100 client configured via Imagine SDK` to confirm it's wired up, instead of a `Cloud AI 100 unavailable, falling back...` warning.

See [`cloud/inference.py`](cloud/inference.py)'s docstring and [`SNAPDRAGON_PC_SETUP.md`](SNAPDRAGON_PC_SETUP.md#7-wiring-the-real-cloud-ai-100-llm-imagine-sdk) for the full env-var contract.

### 3. Mobile app

Requires **Android Studio** (or the command-line SDK + `ANDROID_HOME` set) and **JDK 17+**.

1. Create `mobile/local.properties` (gitignored):

   ```properties
   sdk.dir=/path/to/Android/Sdk
   SARVAM_API_KEY=your-sarvam-key-here
   PC_BASE_URL=http://10.0.2.2:8000
   ```

   `PC_BASE_URL` defaults to `10.0.2.2:8000` (the Android emulator's alias for its host machine). For a **physical device on the same WiFi** as the PC, use the PC's real LAN IP instead (`ip addr` / `ipconfig`), and make sure the PC's firewall allows the port.

2. Build and install:

   ```bash
   cd mobile
   ./gradlew assembleDebug
   adb install -r app/build/outputs/apk/debug/app-debug.apk
   ```

Note: `PC_BASE_URL` is plain `http://`, not `https://`, by design (a local-WiFi-only connection to your own PC) — the manifest explicitly allows cleartext traffic for this reason. See the comment above `<application>` in `AndroidManifest.xml`.

### 4. Browser extension

No build step, but `extension/libs/` (pdf.js, Tesseract.js + its WASM OCR cores and English trained data) is fetched on demand rather than committed — it's ~16MB of unmodified third-party code with no place in this repo's git history. Fetch it once:

```bash
node extension/scripts/fetch_libs.js
```

Each file is pinned to an exact upstream version and sha256-verified after download, so this always reproduces the same bytes. Re-run it any time `extension/libs/` is missing.

Then load it unpacked:

1. Open `chrome://extensions`, enable **Developer mode**.
2. **Load unpacked** → select the `extension/` folder.
3. It POSTs to `http://localhost:8000/index` by default (`PC_ENDPOINT` in `background.js`) — correct as-is when the extension runs on the same PC as the backend, which is the intended deployment.

It captures three kinds of content, all funneling into the same `POST /index` call:
- **Text** (`content_script.js`) — paragraphs/headings/list items visible for 1.5s+, batched and sent once 300+ new characters accumulate (or on tab-hide/navigate-away, whichever comes first).
- **PDFs** (`pdf_capture.js` + offscreen `pdf.js`) — Chrome's built-in PDF viewer blocks content-script injection, so this watches tab navigation instead and extracts text in an offscreen document; falls back to rendering + OCR for scanned/image-only PDFs.
- **Images** (`image_ocr.js` + offscreen Tesseract.js) — runs OCR on images dwelled on for 1.5s+ that are at least 150×150px.

## Configuration reference

| Variable | Component | Default | Purpose |
|---|---|---|---|
| `EMBEDDING_MODEL_PATH` | PC | `models/embedding_gemma_300m_qnn_int8.onnx` | Path to the embedding ONNX model |
| `LANCEDB_PATH` | PC | `lancedb` | LanceDB data directory |
| `EMBEDDING_DIM` | PC | `768` | Embedding vector width — must match the model |
| `WATCH_ROOT` | PC | current user's home directory | Directory the filesystem watcher watches recursively |
| `LOG_FILE` | PC | `lore.log` | Rotating log file path |
| `IMAGINE_API_KEY` | Cloud | *(unset — falls back to a templated answer)* | Imagine SDK API key |
| `IMAGINE_ENDPOINT_URL` | Cloud | SDK default | Imagine SDK endpoint override |
| `IMAGINE_MODEL_NAME` | Cloud | `Llama-3.1-8B` | Model to call for answer generation |
| `sdk.dir` | Mobile (`local.properties`) | — | Path to the Android SDK |
| `SARVAM_API_KEY` | Mobile (`local.properties`) | — | Sarvam AI Speech-to-Text key (voice input) |
| `PC_BASE_URL` | Mobile (`local.properties`) | `http://10.0.2.2:8000` | Backend base URL |
| `PC_ENDPOINT` | Extension (`background.js` constant) | `http://localhost:8000/index` | Backend `/index` endpoint |

## Running the tests

**Python backend** (156 tests):

```bash
pip install -r pc/requirements-dev.txt
pytest
```

**Browser extension** — unit tests (mocked `fetch`) and an integration test (real `fetch` against a live backend), both via Node's built-in test runner, no `npm install` required:

```bash
node --test extension/tests/background.test.js               # unit — always runs
node --test extension/tests/background.test.js extension/tests/background.integration.test.js  # + integration
```

The integration test needs a real backend running at `http://localhost:8000` (`uvicorn pc.api.main:app`) — it skips cleanly with a clear message if none is reachable.

**Mobile** — only the default project-template test currently exists (`ExampleUnitTest.kt`); there's no real coverage of `LoreApiService`/`QueryViewModel` yet. Manual verification against a real device/backend is the current source of truth:

```bash
cd mobile && ./gradlew test        # unit tests (default template only)
./gradlew connectedAndroidTest      # instrumented tests, needs a device/emulator
```

## Current status

Honest snapshot of what's real versus what's aspirational, as of this writing:

**Working end-to-end, verified against real hardware/services:**
- Full request path: mobile app → WiFi → FastAPI → LanceDB search → real Cloud AI 100 (`Llama-3.1-8B` via Imagine SDK) → answer + sources rendered on-device. Verified on a physical Android phone.
- QNN Execution Provider registration in `embedder.py` (FastRPC DLL discovery, `onnxruntime_qnn` library loading, HTP backend path) — real, not a stub.
- A real Gemma tokenizer path in `Embedder.embed()`: auto-detects whether the loaded ONNX model expects `input_ids`/`attention_mask` (real Gemma mode, via `sentencepiece`) versus a single flat vector (toy/smoke-test mode), with attention-mask-aware mean pooling for 3D `last_hidden_state` outputs.
- Browser extension: text/PDF/image capture pipeline, all funneling through the same `/index` contract; 5 unit tests + 1 live integration test passing.
- Duplicate/stale-row prevention on re-indexing (content-hash short-circuiting + delete-before-insert), and clearly distinguished "not configured yet" vs. genuine-error logging on the Cloud AI 100 path.

**Known gaps:**
- `sentencepiece`/`transformers`/`torch` (needed for the real tokenizer path and `pc/scripts/export_vanilla_onnx.py`) aren't yet declared in `pc/requirements*.txt` — install manually until that's added.
- The pre-exported EmbeddingGemma ONNX model uses fused `com.microsoft` ops (`MultiHeadAttention`, `RotaryEmbedding`) that QNN doesn't support, causing silent 100% CPU fallback — `pc/scripts/export_vanilla_onnx.py` re-exports with standard ONNX ops to fix this. This has only been exercised on CPU so far ("quantized embedding model running on cpu rn"); real on-NPU validation is still pending on the actual Snapdragon hardware.
- Mobile app has no automated coverage of its networking/state layer, and its "Recent Searches" list is still hardcoded mock data.
- No authentication on the FastAPI endpoints — acceptable for a local-WiFi-only hackathon demo, not for anything beyond that.
- Image indexing via `jina-clip` (a separate LanceDB table) is a placeholder schema only, per design — deferred to a future phase.
- `.ppt` (legacy PowerPoint format) is not actually supported despite appearing in early planning docs; only `.pptx`.

## Tech stack

| Layer | Technology |
|---|---|
| PC indexing | Python, watchdog, PyMuPDF/pypdf, python-docx, python-pptx, openpyxl, ONNX Runtime (+ QNN execution provider), LanceDB |
| PC API | FastAPI, uvicorn, Pydantic |
| Cloud AI 100 | Cirrascale Imagine SDK 0.4.2, numpy (reranking) |
| Mobile | Kotlin, Jetpack Compose, Material 3, Navigation Compose, OkHttp, MediaRecorder, Sarvam AI Speech-to-Text |
| Browser extension | Manifest V3, pdf.js, Tesseract.js |
| Testing | pytest, Node's built-in test runner (`node:test`) |

## Acknowledgments

Built at the Snapdragon Multiverse Hackathon by Qualcomm India. Sarvam AI (Speech-to-Text) and OnePlus (mobile hardware) are the event's official partners; indexing and embedding run on Snapdragon X NPU hardware via ONNX Runtime's QNN execution provider, and query-time inference runs on Qualcomm Cloud AI 100 via Cirrascale's Imagine SDK.
