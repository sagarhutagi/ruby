# Implementation Roadmap: RUBY

Follow this roadmap strictly in sequential order. A phase is complete only when its acceptance criteria pass and automated tests verify its functionality.

---

## Phase 0 --- Repository inspection and planning
- [x] Inspect current working directory.
- [x] Check available Python, Node, npm, Git and Ollama versions.
- [x] Identify existing files and avoid overwriting them.
- [x] Create `ARCHITECTURE.md`.
- [x] Create `ROADMAP.md`.
- [x] Create `TASKS.md`.
- [x] Create `.gitignore` and `.env.example`.
- [x] Record risks, dependencies and implementation order.

**Acceptance criteria:** Architecture and task breakdown exist, project directory is safe, and no user data was overwritten.

---

## Phase 1 --- Foundation
- [x] Create backend project and dependency management.
- [x] Create frontend React/TypeScript/Vite project.
- [x] Configure Tailwind CSS and UI styling system.
- [x] Create FastAPI application and health endpoint (`/api/v1/health`).
- [x] Configure SQLite and SQLAlchemy 2 async engine.
- [x] Configure Alembic migrations.
- [x] Create application settings and configurable data directory.
- [x] Create initial dashboard and navigation layout.
- [x] Add frontend/backend development and startup scripts.
- [x] Add basic backend and frontend automated tests.

**Acceptance criteria:** Both applications start; frontend can call backend health endpoint; database initialises and migrations run; tests pass.

---

## Phase 2 --- AI provider infrastructure
- [ ] Define provider interfaces and capability declarations.
- [ ] Implement Ollama adapter.
- [ ] Implement OpenAI adapter.
- [ ] Implement Gemini adapter.
- [ ] Implement Anthropic Claude adapter.
- [ ] Implement OpenRouter adapter.
- [ ] Implement generic OpenAI-compatible adapter.
- [ ] Add secure credential storage (Linux keyring + encrypted fallback).
- [ ] Add provider CRUD APIs (`/api/v1/providers`).
- [ ] Add provider connection and latency tests.
- [ ] Add dynamic model discovery where supported.
- [ ] Add streaming chat interface with token counters.
- [ ] Add model routing by task (chat, reasoning, embeddings, tutoring).
- [ ] Add explicit, opt-in fallback rules.
- [ ] Add provider manager GUI.
- [ ] Add mocked adapter tests.

**Acceptance criteria:** A user can add a provider, securely configure it, test it, select a model and receive a streamed response. Secrets never appear in API responses or logs.

---

## Phase 3 --- Hardware and system monitoring
- [ ] Detect CPU and RAM utilization.
- [ ] Detect GPU and VRAM metrics where available via NVML/nvidia-smi.
- [ ] Detect disk usage across application storage partitions.
- [ ] Detect Ollama running status and loaded models.
- [ ] Show model loading/inference status where available.
- [ ] Add hardware-aware model warnings (VRAM limits for 4B-8B quantised models).
- [ ] Add system resource dashboard in UI.
- [ ] Test graceful fallback behavior when monitoring tools or GPUs are absent.

**Acceptance criteria:** Dashboard metrics are real, labelled and gracefully unavailable when unsupported.

---

## Phase 4 --- Document ingestion and library
- [ ] Implement PDF parser (PyMuPDF).
- [ ] Implement DOCX parser (python-docx).
- [ ] Implement PPTX parser (python-pptx).
- [ ] Implement XLSX and CSV parsers (openpyxl/pandas).
- [ ] Implement TXT, Markdown, HTML, JSON and XML parsers.
- [ ] Implement EPUB parser.
- [ ] Implement image OCR (pytesseract).
- [ ] Add optional legacy format conversion.
- [ ] Preserve page, slide, sheet and cell provenance.
- [ ] Implement upload and folder import.
- [ ] Implement SHA-256 duplicate detection.
- [ ] Implement persistent ingestion background jobs.
- [ ] Implement cancellation and retry.
- [ ] Implement subject and collection management.
- [ ] Implement library search, filters and previews.
- [ ] Add parser tests using representative test fixtures.

**Acceptance criteria:** Supported files can be imported, parsed and inspected. Failures are visible and recoverable. The UI remains responsive during ingestion.

---

## Phase 5 --- Embeddings and RAG
- [ ] Implement embedding provider interface.
- [ ] Integrate local embedding models (Sentence Transformers / BGE / nomic).
- [ ] Implement structure-aware and recursive chunking.
- [ ] Configure persistent ChromaDB storage.
- [ ] Configure SQLite FTS5 for keyword search.
- [ ] Implement dense vector retrieval.
- [ ] Implement BM25 keyword retrieval.
- [ ] Implement hybrid ranking (Reciprocal Rank Fusion - RRF).
- [ ] Implement optional reranking.
- [ ] Implement metadata and subject filtering.
- [ ] Implement query rewriting.
- [ ] Implement context assembly.
- [ ] Preserve source provenance end-to-end.
- [ ] Implement citation validation.
- [ ] Implement retrieval diagnostics inspector.
- [ ] Add RAG evaluation dataset and verification tests.

**Acceptance criteria:** A question over imported documents retrieves relevant chunks and produces verifiable citations. Missing evidence is reported rather than invented.

---

## Phase 6 --- Chat experience
- [ ] Implement conversation and message persistence in SQLite.
- [ ] Implement streaming UI with Server-Sent Events (SSE).
- [ ] Implement Markdown and code syntax highlighting.
- [ ] Implement LaTeX equation rendering (KaTeX/MathJax).
- [ ] Implement citations and interactive collapsible source panel.
- [ ] Implement subject/document filtering in chat.
- [ ] Implement Resource-grounded, General, Hybrid, and Research modes.
- [ ] Implement conversation search, rename, and export.
- [ ] Implement stop generation and message regeneration.
- [ ] Show active provider/model and local vs. cloud badges.
- [ ] Add end-to-end chat integration tests.

**Acceptance criteria:** Chat works with local and configured cloud providers, retains conversations, streams responses and displays accurate sources.

---

## Phase 7 --- Memory subsystem
- [ ] Define working, episodic, semantic, profile, and procedural memory schemas.
- [ ] Implement candidate memory extraction.
- [ ] Implement importance scoring.
- [ ] Implement duplicate detection.
- [ ] Implement contradiction handling.
- [ ] Implement configurable memory approval policy.
- [ ] Implement consolidation and semantic retrieval.
- [ ] Implement memory provenance links to conversations/events.
- [ ] Implement edit, pin, and delete actions.
- [ ] Ensure deleting a memory purges all derived and vector indexes.
- [ ] Implement memory audit log.
- [ ] Build Memory Manager UI.
- [ ] Test memory lifecycle, scoring, and deletion.

**Acceptance criteria:** Memories persist independently of chat history, can be inspected and edited, and deletion removes searchable derived representations.

---

## Phase 8 --- Academic tools
- [ ] Implement concept explainer (Beginner, Intermediate, Advanced levels).
- [ ] Implement mathematics tutor with LaTeX solutions and SymPy engine.
- [ ] Implement DSA tutor with visual traces and safe execution sandbox.
- [ ] Implement Computer Networks tutor with protocol flow simulators.
- [ ] Implement DLCD tools (truth tables, K-maps, Boolean logic).
- [ ] Implement Operating Systems tutor (CPU scheduling, memory paging, deadlocks).
- [ ] Implement quiz generation and scoring (MCQ, conceptual, numerical).
- [ ] Implement flashcards with FSRS spaced repetition scheduling.
- [ ] Implement mock examinations with timer, negative marking, and analysis.
- [ ] Implement notes generator (revision sheets, formula sheets, summaries).
- [ ] Implement prerequisite mapping.
- [ ] Implement study session and revision progress tracking.
- [ ] Add comprehensive tests for calculations, scheduling, and execution sandbox.

**Acceptance criteria:** Each academic module performs real operations and persists relevant progress. No generated code runs unsandboxed.

---

## Phase 9 --- Knowledge graph and Obsidian
- [ ] Implement graph node and edge models in SQLite.
- [ ] Implement graph CRUD APIs.
- [ ] Implement React Flow visualization with interactive node inspection.
- [ ] Add subject and relation filtering.
- [ ] Mark unverified AI suggestions with distinctive tags.
- [ ] Implement Obsidian vault path selection.
- [ ] Implement Markdown export with YAML frontmatter and `[[wikilinks]]`.
- [ ] Implement vault conflict preview and overwrite protection.
- [ ] Add integration tests for graph queries and vault export.

**Acceptance criteria:** Users can inspect and edit concept relationships and export notes without accidental vault modification.

---

## Phase 10 --- Analytics and resource diagnostics
- [ ] Implement document analytics (storage, formats, chunk counts).
- [ ] Implement study analytics (time spent, retention, quiz accuracy).
- [ ] Implement AI token usage and latency tracking.
- [ ] Implement reliable cost estimates where pricing tables are known.
- [ ] Implement retrieval inspection UI (scores, queries, assembled context).
- [ ] Implement system diagnostics view.
- [ ] Implement sanitized diagnostic report export (secrets redacted).
- [ ] Verify all displayed statistics reflect measured data.

**Acceptance criteria:** Analytics and diagnostics are derived from actual stored events and system measurements.

---

## Phase 11 --- Security and hardening
- [ ] Review and verify secure secret storage (no plaintext keys in SQLite).
- [ ] Review upload validation and MIME checking.
- [ ] Review path traversal guards on file reads and exports.
- [ ] Review safe archive handling.
- [ ] Review subprocess execution boundaries and sanitization.
- [ ] Review code sandbox limits (timeout, memory, syscall restrictions).
- [ ] Review prompt injection protections in document parsing.
- [ ] Review cloud data disclosure flags.
- [ ] Review deletion cascading and backup integrity.
- [ ] Run security linters and full test suite.
- [ ] Resolve any identified high/critical vulnerabilities.

**Acceptance criteria:** No known critical security issue remains; destructive actions require confirmation; private data is not silently transmitted.

---

## Phase 12 --- Packaging and documentation
- [ ] Create robust startup script (`start.sh`).
- [ ] Create shutdown script (`stop.sh`).
- [ ] Add prerequisite checker for Linux environments.
- [ ] Add environment setup instructions.
- [ ] Add production frontend build and static serving in FastAPI.
- [ ] Add database and file backup and restore scripts.
- [ ] Complete README with quickstart and feature documentation.
- [ ] Complete architecture documentation.
- [ ] Complete API reference documentation.
- [ ] Complete troubleshooting guide.
- [ ] Test clean installation flow on Linux.
- [ ] Verify system restart, state persistence, and backup restoration.

**Acceptance criteria:** A new installation can be started using documented commands, data persists across restarts, and backup restoration works.
