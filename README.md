# RUBY — Personal Academic Intelligence & Research Copilot

[![Python 3.11+](https://img.shields.io/badge/python-3.11%20%7C%203.14-blue.svg)](https://www.python.org/)
[![React 19](https://img.shields.io/badge/react-19.0.0-61dafb.svg)](https://react.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests: 71 Passing](https://img.shields.io/badge/tests-78%20passed-brightgreen.svg)]()

> **A local-first, privacy-respecting academic copilot and knowledge management system.**
> Combining NotebookLM-style grounded document intelligence, Obsidian-compatible knowledge graphs, FSRS v4 spaced repetition, mathematical symbolic verification via SymPy, and interactive subject tutors (OS, DSA, Computer Networks, DLCD).

---

## 🌟 Key Capabilities

### 1. Multi-Format Academic Document Ingestion
- **Formats:** PDF (PyMuPDF with two-column & table extraction), DOCX, PPTX (slide-by-slide), XLSX & CSV (cell-coordinate mapping), HTML/Markdown/JSON/XML, EPUB, and Scanned Image OCR (Tesseract).
- **Exact Provenance:** Every chunk preserves page numbers, slide coordinates, sheet names, cell ranges, or section headings for infallible citation tracing.
- **SHA-256 Deduplication:** Prevents duplicate document storage and vector indexing.

### 2. Hybrid RAG Engine (Vector + FTS5 BM25)
- **Structure-Aware Chunking:** Intelligently preserves code fences, mathematical LaTeX blocks, markdown tables, and header hierarchies without mid-block fragmentation.
- **Reciprocal Rank Fusion (RRF):** Combines dense vector cosine similarity (ChromaDB) with SQLite FTS5 BM25 keyword ranking ($RRF = \sum \frac{w}{60 + rank}$) and academic acronym expansion.
- **Zero Hallucination Grounding:** Real-time post-generation citation validation. Quotes and claims not present in source chunks are automatically flagged with warnings.

### 3. NotebookLM-Style Grounded Conversational AI
- **Four Distinct Modes:**
  - `Resource-grounded`: Restricted strictly to uploaded document context; explicitly declares when evidence is missing.
  - `General`: Unrestricted general conversational assistance with clear visual badges.
  - `Hybrid`: Combines verified source chunks with general model knowledge.
  - `Research`: Multi-step query decomposition and deep synthesis.
- **Server-Sent Events (SSE):** Token-by-token streaming with live citation pills and collapsible source inspector.
- **Rendering:** Inline KaTeX math (`$...$`), block equations (`$$...$$`), syntax-highlighted code blocks with one-click copy.

### 4. Spaced Repetition (FSRS v4) & Examination Hub
- **Free Spaced Repetition Scheduler (FSRS):** Implements modern power-law retention decay curves ($R(t, S) = (1 + t / 9S)^{-1}$) to predict optimal review intervals across 4 recall grades (Again, Hard, Good, Easy).
- **Decks & Card Manager:** KaTeX math formula and code snippet support on flashcards.
- **Automated Mock Exams:** Generates subject assessments with multiple-choice questions, countdown timers, instant automated grading, and pedagogical mistake reviews.

### 5. Interactive Academic Simulators & Sandboxes
- **SymPy Symbolic Mathematics:** Real algebraic equation solver, differentiation (order 1-5), definite/indefinite calculus integration, simplifications, and matrix operations (det, inv, eigenvalues, RREF).
- **Restricted Subprocess Code Sandbox:** Python execution sandbox isolated in temporary directories with static AST security analysis (blocking `os`, `sys`, `subprocess`, `socket`, `eval`, `exec`, and reflection dunder introspection) with a 2.5s execution timeout.
- **DSA Step Tracer:** Visual step-by-step pointers (`low`, `mid`, `high`) for binary search and bubble sort passes.
- **OS CPU Scheduler:** Simulates First-Come First-Served (FCFS) and preemptive Round Robin scheduling with visual Gantt chart timelines and turnaround/waiting time metrics.
- **OS Banker's Algorithm:** Evaluates system resource safety sequences and detects deadlocks.
- **Virtual Memory Page Replacement:** Step-by-step frame state grid and fault rate calculations for FIFO and LRU algorithms.
- **Computer Networks Subnet Calculator:** IPv4 CIDR breakdown, network/broadcast addresses, usable host ranges, and RFC 1918 classification.
- **DLCD Boolean Truth Table:** Automated evaluation of arbitrary boolean expressions with AND, OR, NOT, XOR.

### 6. Interactive Knowledge Graph & Obsidian Exporter
- **React Flow Visualization:** Relational concept maps with color-coded node types (`concept`, `topic`, `formula`, `document`, `subject`) and edge types (`PREREQUISITE_OF`, `RELATED_TO`, `PART_OF`, `EXPLAINED_IN`).
- **Prerequisite Pathway Solver:** Computes topological learning order for any advanced concept.
- **Automatic Concept Extraction:** Derives topics, definitions, and equations from library documents into unverified AI suggestions.
- **Obsidian Vault Exporter:** Generates full Obsidian vaults with YAML frontmatter, tags, `[[wikilinks]]`, and conflict protection against accidental overwrites. Direct `.zip` download supported.

### 7. 5-Tier Memory Subsystem
- **Tiers:** Working, Episodic, Semantic, Profile, Procedural.
- **Features:** Importance scoring, contradiction resolution, candidate extraction, and complete ChromaDB vector purging on memory deletion.

### 8. Multi-Provider AI Architecture & Hardware Telemetry
- **Local-First Default:** Offline Ollama inference is default; cloud providers (OpenAI, Gemini, Claude, OpenRouter) require explicit configuration.
- **Secret Protection:** API keys sealed in Linux Keyring or AES-256-GCM encrypted fallback; never stored in plaintext SQLite or returned in API responses.
- **Real Hardware Telemetry:** NVML / nvidia-smi GPU and VRAM monitoring, psutil CPU/RAM/Disk metrics, and model VRAM fit advisory.

---

## 🚀 Quickstart Guide

### Prerequisites
- **Linux OS** (Ubuntu 22.04+, Debian 12+, Fedora, Arch, etc.)
- **Python 3.11+** (Python 3.14 fully supported)
- **Node.js 18+** & npm
- **Ollama** (optional, for local offline inference: `curl -fsSL https://ollama.ai/install.sh | sh`)
- **NVIDIA GPU** (optional, recommended 4GB-8GB VRAM for local models like `llama3.2:3b` or `qwen2.5:7b`)

Check your system readiness:
```bash
./scripts/check_prerequisites.sh
```

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/ruby.git
   cd ruby
   ```

2. **Setup Backend Python Environment:**
   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   cd ..
   ```

3. **Setup Frontend Dependencies & Build:**
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```

4. **Initialize Environment File:**
   ```bash
   cp .env.example .env
   ```

---

## ⚙️ Running RUBY

### Production Mode (Single Process)
Starts the FastAPI server serving both the REST/SSE backend and compiled React 19 frontend:
```bash
./start.sh
```
- Web Application: **http://127.0.0.1:8000**
- Interactive Swagger API Documentation: **http://127.0.0.1:8000/docs**

To stop the running application:
```bash
./stop.sh
```

### Development Mode (Hot Reload)
Starts backend Uvicorn and Vite frontend dev server concurrently:
```bash
./scripts/dev.sh
```
- Frontend Dev Server: **http://127.0.0.1:5173**
- Backend Dev Server: **http://127.0.0.1:8000**

---

## 🧪 Testing Suite

Run the complete test suite across backend (pytest) and frontend (vitest):
```bash
./scripts/run_tests.sh
```

Run tests individually:
```bash
# Backend tests (71 tests covering all academic engines, security, RAG, and APIs)
backend/.venv/bin/pytest

# Frontend tests (7 tests covering layout, academic study hub, graph, and analytics)
npm --prefix frontend test
```

---

## 💾 Backup & Restore

Create a timestamped archive of the SQLite database, ChromaDB vectors, and uploaded documents:
```bash
# Creates a backup in ./backups/
./scripts/backup.sh
```

Restore a previous backup:
```bash
# Safely restores databases while preserving current data as pre-restore backup
./scripts/restore.sh backups/ruby_backup_<timestamp>.tar.gz
```

---

## 🔒 Security Architecture

- **Localhost-Only Enforcement:** All server bindings are strictly bound to `127.0.0.1` (`localhost`), eliminating external LAN exposure.
- **Zero Silent Cloud Leakage:** Requests are routed to local Ollama by default. Cloud providers require explicit user configuration and toggle.
- **Secret Encryption:** API keys are sealed using the OS Secret Service (Linux Keyring) or salted AES-256-GCM encrypted local store. Plaintext keys are never stored in SQLite or exposed in diagnostic exports.
- **Sandboxed Execution:** Code execution for algorithmic tutors runs in temporary, isolated directories with static AST verification rejecting dangerous builtins, dunder introspection, and network access.

---

## 📄 License
MIT License. Created for students, researchers, and lifelong learners.
