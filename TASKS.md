# Tasks & Work Log: RUBY

## Task Summary
- **Current Phase:** Phase 9 (Knowledge Graph & Obsidian) -> Complete. Beginning Phase 10 (Analytics & Diagnostics)
- **Status:** In Progress
- **Last Updated:** 2026-11-13

---

## Detailed Task Breakdown

### Phase 0: Repository Inspection & Planning
- [x] Inspect current working directory (clean repository, only spec present).
- [x] Verify system toolchain: Python 3.14.9, Node v26.13.1, npm 12.2.2, git 2.56.1, Ollama 0.40.16, NVIDIA RTX 3050 Laptop GPU (6GB VRAM), 24GB RAM.
- [x] Create `.gitignore` and `.env.example`.
- [x] Create `ARCHITECTURE.md`.
- [x] Create `ROADMAP.md`.
- [x] Create `TASKS.md`.
- [x] Document risks, dependencies, and implementation strategy.

### Phase 1: Foundation
- [x] Initialize backend Python environment and directory structure (`backend/app`).
- [x] Define backend dependencies in `requirements.txt` (FastAPI, uvicorn, sqlalchemy, greenlet, aiosqlite, pydantic, pydantic-settings, alembic, httpx, pytest, pytest-asyncio).
- [x] Create `backend/app/core/config.py` with configurable paths and settings.
- [x] Create `backend/app/database/session.py` with async SQLAlchemy SQLite engine and base model.
- [x] Setup Alembic migrations framework in `backend/migrations/` and apply initial schema migration.
- [x] Create initial FastAPI application `backend/app/main.py` with `/api/v1/health` and CORS restricted to localhost.
- [x] Initialize frontend React 19 + TypeScript + Vite project in `frontend/`.
- [x] Configure Tailwind CSS and Lucide icons in frontend.
- [x] Implement core frontend layout (Sidebar, Header, AppLayout) and 10 main pages matching dark-first UI aesthetic.
- [x] Implement frontend API client and TanStack Query integration.
- [x] Create runner scripts: `start.sh`, `stop.sh`, `scripts/dev.sh`, `scripts/run_tests.sh`.
- [x] Write backend unit tests for health check, config, FTS5, and database connection.
- [x] Write frontend unit tests for layout and health status indicator.
- [x] Execute test suite and verify all acceptance criteria for Phase 1.

### Phase 2: AI Provider Infrastructure
- [x] Provider interface and capabilities specification in `app/services/ai/base.py`.
- [x] Ollama adapter with local model listing, generation, and streaming in `adapters/ollama.py`.
- [x] Cloud provider adapters (OpenAI, Gemini, Claude, OpenRouter, Generic OpenAI) with SSE streaming.
- [x] Secret storage with Linux keyring and AES-GCM encrypted fallback in `app/core/secrets_manager.py`.
- [x] Provider management endpoints and CRUD in `app/api/v1/providers.py`.
- [x] Model routing and explicit fallback policies in `app/services/ai/manager.py`.
- [x] Provider manager GUI in `frontend/src/pages/ProvidersPage.tsx`.
- [x] Mocked adapter and secrets unit tests with 100% pass rate.

### Phase 3: Hardware & System Monitoring
- [x] NVML / nvidia-smi GPU and VRAM detector in `app/core/hardware.py`.
- [x] psutil CPU, RAM, and Disk metrics.
- [x] Ollama service health and model status probe.
- [x] Hardware-aware model memory evaluation & warnings (4B-8B vs 14B+ models).
- [x] System resource dashboard component in `frontend/src/pages/AnalyticsPage.tsx`.
- [x] Unit tests for hardware monitoring and graceful fallbacks.

### Phase 4: Document Ingestion & Library
- [x] Multi-format parsers (PDF with PyMuPDF, DOCX, PPTX, XLSX/CSV, HTML/Markdown/JSON/XML, EPUB, Image OCR).
- [x] Provenance preservation (page number, slide number, sheet/cell coordinate, section heading).
- [x] Persistent ingestion background jobs with status tracking and progress reporting.
- [x] SHA-256 duplicate detection preventing redundant storage.
- [x] Subject and collection CRUD APIs and UI management in `app/api/v1/subjects.py` and `collections.py`.
- [x] Document library UI with multi-file upload, format filtering, chunk inspector, and deletion in `frontend/src/pages/LibraryPage.tsx`.
- [x] Comprehensive parser unit tests using representative test fixtures.

### Phase 5: Embeddings & RAG
- [x] Embedding adapter and local SentenceTransformers/ChromaDB store.
- [x] Structure-aware semantic chunking.
- [x] SQLite FTS5 full-text keyword indexing.
- [x] Hybrid search with Reciprocal Rank Fusion (RRF).
- [x] End-to-end citation provenance verification.
- [x] Retrieval diagnostics panel.
- [x] RAG evaluation tests.

### Phase 6: Chat Experience
- [x] SQLite conversation and message persistence.
- [x] SSE streaming chat endpoint and frontend streaming consumer.
- [x] Markdown, KaTeX LaTeX, and syntax-highlighted code rendering.
- [x] Collapsible citation and source inspector panel.
- [x] Answer modes: Resource-grounded, General, Hybrid, Research.
- [x] Chat tests.

### Phase 7: Memory Subsystem
- [x] 5-tier memory models (Working, Episodic, Semantic, Profile, Procedural).
- [x] Candidate extraction and importance scoring.
- [x] Memory consolidation, deduplication, and contradiction resolution.
- [x] Memory manager UI with editing, pinning, and deletion.
- [x] Memory unit tests.


### Phase 8: Academic Learning Tools
- [x] Concept explainer with difficulty levels.
- [x] Mathematics tutor with SymPy calculations.
- [x] DSA tutor with safe subprocess sandbox.
- [x] Computer Networks and DLCD simulators.
- [x] OS process scheduling and memory simulators.
- [x] Quiz engine with multi-format questions.
- [x] Flashcards with FSRS spaced repetition.
- [x] Academic tool tests.

### Phase 9: Knowledge Graph & Obsidian
- [x] Graph node and edge schemas.
- [x] React Flow interactive knowledge graph.
- [x] Obsidian vault exporter with frontmatter and wikilinks.
- [x] Vault conflict handling and tests.

### Phase 10: Analytics & Diagnostics
- [ ] Document and study progress analytics.
- [ ] AI token and latency tracking.
- [ ] System diagnostics and sanitized log export.
- [ ] Verification of real measured data.

### Phase 11: Security & Hardening
- [ ] Comprehensive security audit (inputs, paths, sandbox, secrets).
- [ ] Dependency scanning and vulnerability fixes.

### Phase 12: Packaging & Documentation
- [ ] Production build and static serving.
- [ ] `start.sh`, `stop.sh`, backup/restore scripts.
- [ ] Final user and technical documentation.

---

## Risks, Dependencies & Technical Considerations

1. **Python 3.14 Compatibility**:
   - The host has Python 3.14.9. Some heavy ML packages (e.g., specific PyTorch or sentence-transformers wheels) might require exact wheel availability or source build, or can be bridged with lightweight ONNX / fastembed / sentence-transformers or subprocess inference. We will verify compatibility during dependency installation and provide clean, robust solutions.
2. **GPU & VRAM Constraints**:
   - RTX 3050 has 6GB VRAM. Large models (>8B) cannot fit unquantized. The system must prioritize 3B-8B 4-bit quantizations (e.g. `llama3.2:3b`, `qwen2.5:7b`, `phi3.5`) and warn before running out of memory.
3. **Data Isolation**:
   - All user data, ChromaDB files, raw documents, and SQLite databases must reside in a configurable data directory (`./data` by default) outside source control.
4. **Localhost Only**:
   - All network servers must bind strictly to `127.0.0.1` to prevent unauthorized LAN access.

---

## Log of Completed Work

- **2026-11-13**:
  - Initialized Git repository on `main` branch.
  - Inspected system environment and hardware capabilities.
  - Created `.gitignore` ignoring virtual environments, node modules, build artifacts, and data storage.
  - Created `.env.example` detailing all configuration options.
  - Created `ARCHITECTURE.md` outlining the modular monolith design.
  - Created `ROADMAP.md` tracking all 12 implementation phases.
  - Created `TASKS.md` for continuous task management.
  - Completed Phase 0 acceptance criteria.

---

## Next Steps

1. Begin **Phase 1: Foundation**.
2. Create Python virtual environment and backend directory structure.
3. Install backend core requirements (FastAPI, uvicorn, SQLAlchemy, aiosqlite, pydantic-settings, etc.).
4. Scaffold frontend using Vite (React 19 + TypeScript + Tailwind CSS).
5. Implement backend config, database session, health check API, and verify with tests.
