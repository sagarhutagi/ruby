# Architecture Specification: RUBY

## 1. System Overview

**Ruby** is a local-first, AI-powered personal academic intelligence and knowledge management system designed for Linux (specifically Arch Linux and CachyOS). It unifies document intelligence (NotebookLM style), knowledge management (Obsidian style), conversational AI (ChatGPT style), spaced repetition flashcards (Anki/FSRS style), and interactive academic tutoring (DSA, Math, Computer Networks, DLCD, OS) into a modular monolith.

```
+-----------------------------------------------------------------------------------+
|                                  USER / CLIENT                                    |
|                      Desktop Browser / Web App (Localhost)                         |
+-----------------------------------------------------------------------------------+
                                         │ HTTP / SSE / WebSocket
                                         ▼
+-----------------------------------------------------------------------------------+
|                         FRONTEND (React 19 + TypeScript)                          |
|  - Vite, Tailwind CSS, Lucide React, shadcn/ui                                    |
|  - TanStack Query (Server State), Zustand (Client State), React Router            |
|  - React Flow (Knowledge Graph), Recharts (System & Study Analytics)              |
+-----------------------------------------------------------------------------------+
                                         │ JSON API & Server-Sent Events (SSE)
                                         ▼
+-----------------------------------------------------------------------------------+
|                         BACKEND (FastAPI + Async Python)                          |
|  - FastAPI (REST & Streaming Endpoints, CORS restricted to localhost)             |
|  - Core: Config, Security & Keyring, Hardware Monitoring (NVML/psutil)            |
|  - Services:                                                                      |
|    * AI Provider Manager (Ollama, OpenAI, Gemini, Claude, OpenRouter)             |
|    * Document Ingestion (PyMuPDF, docx, pptx, openpyxl, Tesseract OCR)            |
|    * Chunking & Structure Extraction                                              |
|    * Hybrid Retrieval & RAG (Vector + SQLite FTS5 Keyword + RRF Reranking)        |
|    * Memory Subsystem (Working, Episodic, Semantic, Profile, Procedural)          |
|    * Academic Engines (Math/SymPy, DSA Sandbox, CN, DLCD, OS, Quiz, Flashcard/FSRS)|
|    * Knowledge Graph Engine & Obsidian Vault Exporter                             |
|  - Async Background Task Manager (Ingestion, Indexing, Memory Consolidation)      |
+-----------------------------------------------------------------------------------+
                                  │                │
            ┌─────────────────────┴───────┐        └────────────────────────┐
            ▼                             ▼                                 ▼
+-----------------------+     +-----------------------+     +-------------------------------+
|  RELATIONAL STORAGE   |     |    VECTOR STORAGE     |     |       LOCAL FILESYSTEM        |
| - SQLite 3            |     | - ChromaDB (Embedded) |     | - Raw Uploaded Documents      |
| - SQLAlchemy 2 (async)|     | - Persistent on disk  |     | - Generated Exports & Notes   |
| - SQLite FTS5 index   |     | - Local embeddings    |     | - OCR & Extracted Cache       |
| - Alembic migrations  |     |   (Sentence-Transf.)  |     | - Vault Directory (Obsidian)  |
+-----------------------+     +-----------------------+     +-------------------------------+
```

---

## 2. Component Design & Responsibilities

### 2.1 Backend Modules (`backend/app/`)

- **`core/`**:
  - `config.py`: Environment-driven settings using Pydantic Settings (paths, limits, defaults).
  - `security.py`: Token generation, input sanitization, path traversal guards, secret masking.
  - `secrets_manager.py`: Linux Secret Service / OS keyring integration with AES-GCM encrypted fallback file.
  - `hardware.py`: Real-time GPU (NVML/nvidia-smi), CPU, RAM, disk diagnostics.
- **`database/`**:
  - `session.py`: Async SQLite engine and session factory (`aiosqlite`).
  - `fts.py`: SQLite FTS5 table initialization and full-text search triggers.
- **`models/`**:
  - SQLAlchemy 2 Declarative models for providers, secrets, subjects, collections, documents, chunks, conversations, messages, memories, flashcards, quizzes, study sessions, and graph elements.
- **`schemas/`**:
  - Pydantic v2 validation models for all API requests and responses.
- **`services/ai/`**:
  - `base.py`: Abstract `BaseAIProvider` declaring capabilities (chat, stream, embed, vision).
  - `manager.py`: Provider registry, routing by task (chat, reasoning, summarization, etc.), health tests.
  - `ollama.py`: Local Ollama client (HTTP API, model discovery, model pull/delete).
  - `openai_provider.py`, `gemini.py`, `claude.py`, `openrouter.py`, `generic_openai.py`.
- **`services/documents/`**:
  - Format-specific parsers: `pdf.py` (PyMuPDF), `docx.py`, `pptx.py`, `tabular.py` (openpyxl/pandas), `ocr.py` (pytesseract), `markup.py` (HTML/Markdown/JSON/XML/EPUB).
  - Preserves exact source locations: page number, slide number, sheet/cell coordinate, section heading.
- **`services/retrieval/`**:
  - `chunker.py`: Recursive, structure-aware chunking preserving headings and table boundaries.
  - `chroma_store.py`: ChromaDB persistent client wrapper.
  - `hybrid.py`: Combines ChromaDB vector similarities and SQLite FTS5 scores using Reciprocal Rank Fusion (RRF).
  - `provenance.py`: Citation validator and context assembler.
- **`services/memory/`**:
  - Manages five distinct memory tiers: Working, Episodic, Semantic, User Profile, Procedural.
  - Pipeline: Candidate Extraction -> Importance Scoring -> Duplicate/Contradiction Check -> Approval Policy -> Consolidation -> Retrieval.
- **`services/academic/`**:
  - `math_tutor.py`: LaTeX generation, SymPy symbolic validation.
  - `dsa_tutor.py`: Algorithm visualizer, restricted code execution sandbox.
  - `cn_tutor.py`: OSI/TCP packet flow and networking simulators.
  - `dlcd_tutor.py`: Truth table generator, K-map solver, Boolean minimizer.
  - `os_tutor.py`: Process scheduler, paging/segmentation and deadlock simulator.
  - `flashcards.py`: FSRS spaced repetition implementation.
  - `quiz_engine.py`: Dynamic exam and quiz generator with question-level diagnostic review.
- **`services/knowledge_graph/`**:
  - SQLite-backed graph relations (`PREREQUISITE_OF`, `RELATED_TO`, `EXPLAINED_IN`, `PART_OF`, `CONTRADICTS`).
  - Obsidian export engine with YAML frontmatter, wiki links `[[Concept]]`, and conflict protection.

---

## 3. Data Flow

### 3.1 Document Ingestion Flow
1. File uploaded via `/api/v1/documents/upload`.
2. SHA-256 hash calculated to detect duplicates.
3. Raw file saved to `RUBY_DATA_DIR/documents/<hash>.<ext>`.
4. Background worker parses document structure (pages, headings, tables).
5. Chunker segments content into semantic blocks with provenance metadata.
6. Local embedding model computes dense vectors.
7. Dense vectors saved to ChromaDB; plain text and metadata indexed in SQLite FTS5.
8. Background job updates document state to `indexed`.

### 3.2 Query & RAG Retrieval Flow
1. User submits query in Chat (`/api/v1/chat`).
2. Query is routed to Hybrid Retriever:
   - Vector search on ChromaDB (cosine similarity).
   - Keyword search on SQLite FTS5 (BM25 ranking).
3. Reciprocal Rank Fusion (RRF) combines ranked lists.
4. Top-$k$ chunks pass through optional reranking and relevance thresholding.
5. Relevant memories are retrieved from Memory Service.
6. Grounded context with strict citation tokens (`[Doc: <id>, Page: <p>]`) is assembled.
7. Model streams completion via SSE.
8. Citations are verified against actual chunk texts before display.

---

## 4. Security & Safety Principles

1. **Localhost Binding**: All backend servers bind strictly to `127.0.0.1`.
2. **Zero Cloud Leakage**: Local inference is default. Requests never leave the machine without explicit user selection of a cloud provider.
3. **Secret Storage**: Plaintext API keys are never stored in SQLite or logged. Stored in Linux Secret Service (freedesktop Secret Service API) with AES-GCM encrypted local fallback file.
4. **Untrusted Document Sandbox**: Text extracted from documents is treated as untrusted data; prompt injections cannot override system safety boundaries or execute host commands.
5. **Safe Code Execution**: DSA tutor code dry-runs operate in a restricted subprocess with memory limits, timeouts (max 2 seconds), no network access, and restricted file system permissions.
6. **Destructive Action Protections**: All deletions (documents, memories, graph nodes) require confirmation and cascading cleanups.
