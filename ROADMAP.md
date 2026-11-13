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
- [x] Define provider interfaces and capability declarations.
- [x] Implement Ollama adapter.
- [x] Implement OpenAI adapter.
- [x] Implement Gemini adapter.
- [x] Implement Anthropic Claude adapter.
- [x] Implement OpenRouter adapter.
- [x] Implement generic OpenAI-compatible adapter.
- [x] Add secure credential storage (Linux keyring + encrypted fallback).
- [x] Add provider CRUD APIs (`/api/v1/providers`).
- [x] Add provider connection and latency tests.
- [x] Add dynamic model discovery where supported.
- [x] Add streaming chat interface with token counters.
- [x] Add model routing by task (chat, reasoning, embeddings, tutoring).
- [x] Add explicit, opt-in fallback rules.
- [x] Add provider manager GUI.
- [x] Add mocked adapter tests.

**Acceptance criteria:** A user can add a provider, securely configure it, test it, select a model and receive a streamed response. Secrets never appear in API responses or logs.

---

## Phase 3 --- Hardware and system monitoring
- [x] Detect CPU and RAM utilization.
- [x] Detect GPU and VRAM metrics where available via NVML/nvidia-smi.
- [x] Detect disk usage across application storage partitions.
- [x] Detect Ollama running status and loaded models.
- [x] Show model loading/inference status where available.
- [x] Add hardware-aware model warnings (VRAM limits for 4B-8B quantised models).
- [x] Add system resource dashboard in UI.
- [x] Test graceful fallback behavior when monitoring tools or GPUs are absent.

**Acceptance criteria:** Dashboard metrics are real, labelled and gracefully unavailable when unsupported.

---

## Phase 4 --- Document ingestion and library
- [x] Implement PDF parser (PyMuPDF).
- [x] Implement DOCX parser (python-docx).
- [x] Implement PPTX parser (python-pptx).
- [x] Implement XLSX and CSV parsers (openpyxl/pandas).
- [x] Implement TXT, Markdown, HTML, JSON and XML parsers.
- [x] Implement EPUB parser.
- [x] Implement image OCR (pytesseract).
- [x] Add optional legacy format conversion.
- [x] Preserve page, slide, sheet and cell provenance.
- [x] Implement upload and folder import.
- [x] Implement SHA-256 duplicate detection.
- [x] Implement persistent ingestion background jobs.
- [x] Implement cancellation and retry.
- [x] Implement subject and collection management.
- [x] Implement library search, filters and previews.
- [x] Add parser tests using representative test fixtures.

**Acceptance criteria:** Supported files can be imported, parsed and inspected. Failures are visible and recoverable. The UI remains responsive during ingestion.

---

## Phase 5 --- Embeddings and RAG
- [x] Implement embedding provider interface.
- [x] Integrate local embedding models (Sentence Transformers / BGE / nomic / LocalDense).
- [x] Implement structure-aware and recursive chunking.
- [x] Configure persistent ChromaDB storage.
- [x] Configure SQLite FTS5 for keyword search.
- [x] Implement dense vector retrieval.
- [x] Implement BM25 keyword retrieval.
- [x] Implement hybrid ranking (Reciprocal Rank Fusion - RRF).
- [x] Implement optional reranking.
- [x] Implement metadata and subject filtering.
- [x] Implement query rewriting.
- [x] Implement context assembly.
- [x] Preserve source provenance end-to-end.
- [x] Implement citation validation.
- [x] Implement retrieval diagnostics inspector.
- [x] Add RAG evaluation dataset and verification tests.

**Acceptance criteria:** A question over imported documents retrieves relevant chunks and produces verifiable citations. Missing evidence is reported rather than invented.

---

## Phase 6 --- Chat experience
- [x] Implement conversation and message persistence in SQLite.
- [x] Implement streaming UI with Server-Sent Events (SSE).
- [x] Implement Markdown and code syntax highlighting.
- [x] Implement LaTeX equation rendering (KaTeX/MathJax).
- [x] Implement citations and interactive collapsible source panel.
- [x] Implement subject/document filtering in chat.
- [x] Implement Resource-grounded, General, Hybrid, and Research modes.
- [x] Implement conversation search, rename, and export.
- [x] Implement stop generation and message regeneration.
- [x] Show active provider/model and local vs. cloud badges.
- [x] Add end-to-end chat integration tests.

**Acceptance criteria:** Chat works with local and configured cloud providers, retains conversations, streams responses and displays accurate sources.

---

## Phase 7 --- Memory subsystem
- [x] Define working, episodic, semantic, profile, and procedural memory schemas.
- [x] Implement candidate memory extraction.
- [x] Implement importance scoring.
- [x] Implement duplicate detection.
- [x] Implement contradiction handling.
- [x] Implement configurable memory approval policy.
- [x] Implement consolidation and semantic retrieval.
- [x] Implement memory provenance links to conversations/events.
- [x] Implement edit, pin, and delete actions.
- [x] Ensure deleting a memory purges all derived and vector indexes.
- [x] Implement memory audit log.
- [x] Build Memory Manager UI.
- [x] Test memory lifecycle, scoring, and deletion.

**Acceptance criteria:** Memories persist independently of chat history, can be inspected and edited, and deletion removes searchable derived representations.

---

## Phase 8 --- Academic tools
- [x] Implement concept explainer (Beginner, Intermediate, Advanced levels).
- [x] Implement mathematics tutor with LaTeX solutions and SymPy engine.
- [x] Implement DSA tutor with visual traces and safe execution sandbox.
- [x] Implement Computer Networks tutor with protocol flow simulators.
- [x] Implement DLCD tools (truth tables, K-maps, Boolean logic).
- [x] Implement Operating Systems tutor (CPU scheduling, memory paging, deadlocks).
- [x] Implement quiz generation and scoring (MCQ, conceptual, numerical).
- [x] Implement flashcards with FSRS spaced repetition scheduling.
- [x] Implement mock examinations with timer, negative marking, and analysis.
- [x] Implement notes generator (revision sheets, formula sheets, summaries).
- [x] Implement prerequisite mapping.
- [x] Implement study session and revision progress tracking.
- [x] Add comprehensive tests for calculations, scheduling, and execution sandbox.

**Acceptance criteria:** Each academic module performs real operations and persists relevant progress. No generated code runs unsandboxed.

---

## Phase 9 --- Knowledge graph and Obsidian
- [x] Implement graph node and edge models in SQLite.
- [x] Implement graph CRUD APIs.
- [x] Implement React Flow visualization with interactive node inspection.
- [x] Add subject and relation filtering.
- [x] Mark unverified AI suggestions with distinctive tags.
- [x] Implement Obsidian vault path selection.
- [x] Implement Markdown export with YAML frontmatter and `[[wikilinks]]`.
- [x] Implement vault conflict preview and overwrite protection.
- [x] Add integration tests for graph queries and vault export.

**Acceptance criteria:** Users can inspect and edit concept relationships and export notes without accidental vault modification.

---

## Phase 10 --- Analytics and resource diagnostics
- [x] Implement document analytics (storage, formats, chunk counts).
- [x] Implement study analytics (time spent, retention, quiz accuracy).
- [x] Implement AI token usage and latency tracking.
- [x] Implement reliable cost estimates where pricing tables are known.
- [x] Implement retrieval inspection UI (scores, queries, assembled context).
- [x] Implement system diagnostics view.
- [x] Implement sanitized diagnostic report export (secrets redacted).
- [x] Verify all displayed statistics reflect measured data.

**Acceptance criteria:** Analytics and diagnostics are derived from actual stored events and system measurements.

---

## Phase 11 --- Security and hardening
- [x] Review and verify secure secret storage (no plaintext keys in SQLite).
- [x] Review upload validation and MIME checking.
- [x] Review path traversal guards on file reads and exports.
- [x] Review safe archive handling.
- [x] Review subprocess execution boundaries and sanitization.
- [x] Review code sandbox limits (timeout, memory, syscall restrictions).
- [x] Review prompt injection protections in document parsing.
- [x] Review cloud data disclosure flags.
- [x] Review deletion cascading and backup integrity.
- [x] Run security linters and full test suite.
- [x] Resolve any identified high/critical vulnerabilities.

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
