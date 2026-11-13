# RUBY — REST & Streaming API Reference

The RUBY backend provides a local-first REST and Server-Sent Events (SSE) API bound strictly to `127.0.0.1:8000/api/v1`.
Interactive Swagger documentation is available at `http://127.0.0.1:8000/docs`.

---

## 1. System & Telemetry (`/system`)
- `GET /api/v1/system/resources`: Live hardware telemetry (CPU percentage, RAM total/used/free, GPU VRAM & temperature, NVMe disk space, Ollama daemon status).
- `GET /api/v1/system/model-check?model=<model_name>`: Evaluates whether a target LLM fits within current physical VRAM capacity.

## 2. AI Providers & Routing (`/providers`)
- `GET /api/v1/providers`: List all configured providers (Ollama, OpenAI, Gemini, Claude, OpenRouter) with masked keys.
- `POST /api/v1/providers`: Register or configure an AI provider.
- `PATCH /api/v1/providers/{id}`: Update provider settings (default status, temperature, timeout).
- `DELETE /api/v1/providers/{id}`: Delete provider configuration.
- `POST /api/v1/providers/{id}/test`: Test live connectivity and latency.
- `GET /api/v1/providers/discover/local`: Scan local Ollama instance for installed models.

## 3. Subjects & Collections (`/subjects`, `/collections`)
- `GET /api/v1/subjects`: List academic subjects with document & collection counts.
- `POST /api/v1/subjects`: Create a new academic subject.
- `DELETE /api/v1/subjects/{id}`: Delete a subject.
- `GET /api/v1/collections`: List collections within a subject.
- `POST /api/v1/collections`: Create a collection.
- `DELETE /api/v1/collections/{id}`: Delete a collection.

## 4. Document Ingestion & Library (`/documents`)
- `POST /api/v1/documents/upload`: Multi-file upload with MIME/extension validation and SHA-256 duplicate detection.
- `GET /api/v1/documents`: List documents with filters (`q`, `subject_id`, `file_type`, `status`).
- `GET /api/v1/documents/{id}`: Get document details.
- `DELETE /api/v1/documents/{id}`: Delete document, chunks, FTS index, and ChromaDB vector embeddings.
- `GET /api/v1/documents/{id}/chunks`: Inspect extracted structure-aware chunks.
- `GET /api/v1/documents/jobs/{job_id}`: Track ingestion job progress percentage and stage.

## 5. Retrieval & RAG (`/retrieval`)
- `POST /api/v1/retrieval/search`: Hybrid search with Reciprocal Rank Fusion (RRF), acronym expansion, and subject filtering.
- `POST /api/v1/retrieval/inspect`: Diagnostic inspection of query expansion, sparse BM25 scores, and vector distances.
- `POST /api/v1/retrieval/validate-citation`: Validate citations and quotes against ground-truth document chunks.
- `GET /api/v1/retrieval/stats`: ChromaDB vector collection and chunk statistics.

## 6. Chat & Conversational Intelligence (`/chat`)
- `GET /api/v1/chat/conversations`: List user conversations with subject filters.
- `POST /api/v1/chat/conversations`: Create a new conversation.
- `GET /api/v1/chat/conversations/{id}`: Retrieve message history.
- `PATCH /api/v1/chat/conversations/{id}`: Rename conversation.
- `DELETE /api/v1/chat/conversations/{id}`: Delete conversation.
- `GET /api/v1/chat/conversations/{id}/export`: Export conversation as formatted Markdown.
- `POST /api/v1/chat/stream`: Server-Sent Events (SSE) token streaming endpoint supporting 4 answer modes (`resource-grounded`, `general`, `hybrid`, `research`).
- `POST /api/v1/chat/message`: Synchronous non-streaming chat fallback.
- `POST /api/v1/chat/regenerate/{conversation_id}`: Re-run generation with updated parameters.

## 7. Memory Subsystem (`/memories`)
- `GET /api/v1/memories`: Query 5-tier memories with category filters and search.
- `POST /api/v1/memories`: Create memory record.
- `PATCH /api/v1/memories/{id}`: Edit memory content, importance score, or type.
- `DELETE /api/v1/memories/{id}`: Delete memory and purge its ChromaDB embeddings.
- `POST /api/v1/memories/{id}/pin`: Toggle memory pinning.
- `POST /api/v1/memories/search`: Semantic vector search over memories.
- `POST /api/v1/memories/extract-candidates`: Extract candidate memories from conversation text.
- `GET /api/v1/memories/audit/trail`: Audit log of memory creation, consolidation, and deletions.
- `GET /api/v1/memories/export`: Export memories as JSON.
- `POST /api/v1/memories/import`: Import memories from JSON.

## 8. Academic Learning Tools & Simulators (`/academic`)
- `POST /api/v1/academic/math/solve`: Solve algebraic equations symbolically via SymPy.
- `POST /api/v1/academic/math/diff`: Differentiate mathematical expressions (orders 1-5).
- `POST /api/v1/academic/math/integrate`: Compute definite or indefinite calculus integrals.
- `POST /api/v1/academic/math/simplify`: Simplify algebraic expressions.
- `POST /api/v1/academic/math/matrix`: Compute determinant, inverse, eigenvalues, or RREF of matrices.
- `POST /api/v1/academic/sandbox/run`: Safely execute Python code in an AST-restricted, timeout-bounded sandbox.
- `POST /api/v1/academic/dsa/trace`: Step-by-step visual algorithmic trace (binary search, bubble sort).
- `POST /api/v1/academic/simulators/cpu-schedule`: Simulate FCFS or Round Robin CPU scheduling with Gantt timeline.
- `POST /api/v1/academic/simulators/banker`: Banker's deadlock safety algorithm evaluation.
- `POST /api/v1/academic/simulators/page-replacement`: Simulate FIFO or LRU virtual memory page replacement.
- `POST /api/v1/academic/simulators/subnet`: IPv4 CIDR subnet calculation.
- `POST /api/v1/academic/simulators/truth-table`: Boolean logic truth table generator.
- `GET /api/v1/academic/flashcards/decks`: List flashcard decks with due card counts.
- `POST /api/v1/academic/flashcards/decks`: Create flashcard deck.
- `DELETE /api/v1/academic/flashcards/decks/{id}`: Delete deck and cards.
- `GET /api/v1/academic/flashcards/decks/{id}/cards`: List cards in deck (with `due_only` filter).
- `POST /api/v1/academic/flashcards/cards`: Add new flashcard.
- `POST /api/v1/academic/flashcards/cards/{id}/review`: Submit recall grade (1-4) to update FSRS parameters.
- `GET /api/v1/academic/quizzes`: List academic examination sessions.
- `POST /api/v1/academic/quizzes/generate`: Build custom academic mock exam.
- `GET /api/v1/academic/quizzes/{id}`: Fetch quiz questions.
- `POST /api/v1/academic/quizzes/{id}/submit`: Grade quiz submission and generate pedagogical error analysis.

## 9. Knowledge Graph & Obsidian Exporter (`/graph`)
- `GET /api/v1/graph`: Fetch graph nodes and edges with subject and type filtering.
- `POST /api/v1/graph/nodes`: Create concept node.
- `PATCH /api/v1/graph/nodes/{id}`: Update node label, description, position, or verification.
- `DELETE /api/v1/graph/nodes/{id}`: Delete node and attached edges.
- `POST /api/v1/graph/edges`: Create relationship edge (`PREREQUISITE_OF`, `RELATED_TO`, `PART_OF`, `EXPLAINED_IN`).
- `DELETE /api/v1/graph/edges/{id}`: Delete edge.
- `GET /api/v1/graph/prerequisites/{node_id}`: Compute topological prerequisite learning path.
- `POST /api/v1/graph/extract-from-document/{document_id}`: Auto-extract concepts from document chunks.
- `POST /api/v1/graph/obsidian/preview`: Preview vault export files and conflict warnings.
- `POST /api/v1/graph/obsidian/export`: Export notes with YAML frontmatter and `[[wikilinks]]` to local directory.
- `GET /api/v1/graph/obsidian/export-zip`: Download entire Obsidian vault as a `.zip` archive.

## 10. Analytics & System Diagnostics (`/analytics`)
- `GET /api/v1/analytics/overview`: Composite system analytics (documents, study, tokens).
- `GET /api/v1/analytics/documents`: Storage, formats, and chunk counts.
- `GET /api/v1/analytics/study`: FSRS retention curves, ratings distribution, and quiz accuracy.
- `GET /api/v1/analytics/tokens`: Token consumption and cloud cost estimates.
- `GET /api/v1/analytics/diagnostics`: Sanitized diagnostic health report (secrets redacted).
- `GET /api/v1/analytics/diagnostics/export`: Download sanitized diagnostics as JSON.
