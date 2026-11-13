import { HealthStatus } from '../types';

const API_BASE = '/api/v1';

export async function fetchHealth(): Promise<HealthStatus> {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed with status: ${response.status}`);
  }
  return response.json();
}

export interface ProviderItem {
  id: string;
  name: string;
  provider_type: 'ollama' | 'openai' | 'gemini' | 'anthropic' | 'openrouter' | 'generic';
  base_url?: string;
  model_name: string;
  is_enabled: boolean;
  is_default: boolean;
  timeout_seconds: number;
  temperature: number;
  max_tokens?: number;
  context_window?: number;
  has_api_key: boolean;
  masked_key?: string;
  created_at: string;
  updated_at: string;
}

export interface ProviderCreateModel {
  name: string;
  provider_type: string;
  base_url?: string;
  model_name: string;
  api_key?: string;
  is_enabled: boolean;
  is_default: boolean;
  timeout_seconds: number;
  temperature: number;
  max_tokens?: number;
}

export interface TestResult {
  success: boolean;
  latency_ms: number;
  message: string;
  model_count?: number;
}

export interface DiscoveredModel {
  id: string;
  name: string;
  provider_type: string;
  capabilities: string[];
  context_window?: number;
  is_local: boolean;
  description?: string;
}

export interface SystemResources {
  cpu: {
    percent: number;
    core_count: number;
    frequency_mhz?: number;
  };
  ram: {
    total_mb: number;
    used_mb: number;
    available_mb: number;
    percent: number;
  };
  disk: {
    total_gb: number;
    used_gb: number;
    free_gb: number;
    percent: number;
    path: string;
  };
  gpu: {
    available: boolean;
    name?: string;
    vram_total_mb: number;
    vram_used_mb: number;
    vram_free_mb: number;
    utilization_percent: number;
    temperature_c?: number;
    error?: string;
  };
  ollama: {
    running: boolean;
    version?: string;
    installed_models: string[];
    running_models: string[];
    error?: string;
  };
}

export interface ModelFitResult {
  model_name: string;
  estimated_params_b: number;
  estimated_vram_needed_mb: number;
  vram_available_mb: number;
  fit_tier: 'optimal' | 'tight' | 'exceeds_vram';
  recommendation: string;
  warning?: string;
}

export interface DocumentItem {
  id: string;
  title: string;
  filename: string;
  file_type: string;
  file_size_bytes: number;
  file_hash: string;
  page_count?: number;
  status: 'pending' | 'parsing' | 'indexed' | 'failed';
  error_message?: string;
  subject_id?: string;
  collection_id?: string;
  chunk_count: number;
  meta_info?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface DocumentChunkItem {
  id: string;
  document_id: string;
  chunk_index: number;
  content: string;
  token_count: number;
  page_number?: number;
  slide_number?: number;
  sheet_name?: string;
  cell_range?: string;
  section_heading?: string;
  meta_info?: Record<string, any>;
}

export interface IngestionJobStatus {
  id: string;
  document_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  stage: string;
  progress_percentage: number;
  error_message?: string;
}

// Providers API
export async function fetchProviders(): Promise<ProviderItem[]> {
  const res = await fetch(`${API_BASE}/providers`);
  if (!res.ok) throw new Error('Failed to fetch providers');
  return res.json();
}

export async function createProvider(data: ProviderCreateModel): Promise<ProviderItem> {
  const res = await fetch(`${API_BASE}/providers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to create provider');
  }
  return res.json();
}

export async function deleteProvider(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/providers/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to delete provider');
}

export async function testProvider(id: string): Promise<TestResult> {
  const res = await fetch(`${API_BASE}/providers/${id}/test`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to test provider');
  return res.json();
}

export async function fetchProviderModels(id: string): Promise<DiscoveredModel[]> {
  const res = await fetch(`${API_BASE}/providers/${id}/models`);
  if (!res.ok) throw new Error('Failed to discover models');
  return res.json();
}

// System API
export async function fetchSystemResources(): Promise<SystemResources> {
  const res = await fetch(`${API_BASE}/system/resources`);
  if (!res.ok) throw new Error('Failed to fetch system telemetry');
  return res.json();
}

export async function checkModelFit(model: string): Promise<ModelFitResult> {
  const res = await fetch(`${API_BASE}/system/model-check?model=${encodeURIComponent(model)}`);
  if (!res.ok) throw new Error('Failed to evaluate model memory fit');
  return res.json();
}

// Documents API
export async function fetchDocuments(params?: {
  q?: string;
  subject_id?: string;
  collection_id?: string;
  status?: string;
  file_type?: string;
}): Promise<DocumentItem[]> {
  const query = new URLSearchParams();
  if (params?.q) query.append('q', params.q);
  if (params?.subject_id) query.append('subject_id', params.subject_id);
  if (params?.collection_id) query.append('collection_id', params.collection_id);
  if (params?.status) query.append('status', params.status);
  if (params?.file_type) query.append('file_type', params.file_type);

  const res = await fetch(`${API_BASE}/documents?${query.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch documents');
  return res.json();
}

export async function uploadDocument(
  file: File,
  subject_id?: string,
  collection_id?: string
): Promise<{ document_id: string; job_id: string; is_duplicate: boolean; message: string }> {
  const formData = new FormData();
  formData.append('files', file);
  if (subject_id) formData.append('subject_id', subject_id);
  if (collection_id) formData.append('collection_id', collection_id);

  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error('Document upload failed');
  const list = await res.json();
  return list[0];
}

export async function deleteDocument(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/documents/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to delete document');
}

export async function fetchDocumentChunks(id: string): Promise<DocumentChunkItem[]> {
  const res = await fetch(`${API_BASE}/documents/${id}/chunks`);
  if (!res.ok) throw new Error('Failed to fetch chunks');
  return res.json();
}

export async function fetchJobStatus(jobId: string): Promise<IngestionJobStatus> {
  const res = await fetch(`${API_BASE}/documents/jobs/${jobId}`);
  if (!res.ok) throw new Error('Failed to fetch job status');
  return res.json();
}

// Retrieval & RAG API
export interface RetrievedChunk {
  chunk_id: string;
  document_id: string;
  document_title: string;
  content: string;
  token_count: number;
  page_number?: number | null;
  slide_number?: number | null;
  sheet_name?: string | null;
  cell_range?: string | null;
  section_heading?: string | null;
  dense_rank?: number | null;
  sparse_rank?: number | null;
  dense_score: number;
  sparse_score: number;
  rrf_score: number;
  matched_by: 'both' | 'dense' | 'sparse' | string;
  snippet?: string | null;
}

export interface HybridRetrievalResult {
  query: string;
  expanded_query?: string | null;
  total_found: number;
  dense_count: number;
  sparse_count: number;
  dense_latency_ms: number;
  sparse_latency_ms: number;
  total_latency_ms: number;
  chunks: RetrievedChunk[];
}

export interface RetrievalInspectResponse {
  query: string;
  expanded_query?: string | null;
  total_found: number;
  dense_count: number;
  sparse_count: number;
  dense_latency_ms: number;
  sparse_latency_ms: number;
  total_latency_ms: number;
  fused_chunks: RetrievedChunk[];
  sample_context: string;
}

export async function executeHybridSearch(params: {
  query: string;
  top_k?: number;
  subject_id?: string;
  document_ids?: string[];
  dense_weight?: number;
  sparse_weight?: number;
}): Promise<HybridRetrievalResult> {
  const res = await fetch(`${API_BASE}/retrieval/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error('Hybrid search failed');
  return res.json();
}

export async function inspectRetrieval(params: {
  query: string;
  top_k?: number;
  subject_id?: string;
  document_ids?: string[];
  dense_weight?: number;
  sparse_weight?: number;
}): Promise<RetrievalInspectResponse> {
  const res = await fetch(`${API_BASE}/retrieval/inspect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error('Retrieval inspect failed');
  return res.json();
}

export async function fetchRetrievalStats(): Promise<{
  chroma: { collection_name: string; persist_dir: string; total_chunks: number };
  embedding_provider: string;
  embedding_model: string;
  dimension: number;
}> {
  const res = await fetch(`${API_BASE}/retrieval/stats`);
  if (!res.ok) throw new Error('Failed to fetch retrieval stats');
  return res.json();
}

// Conversation & Chat API
export interface ConversationItem {
  id: string;
  title: string;
  subject_id?: string | null;
  system_prompt?: string | null;
  message_count: number;
  last_message_preview?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatMessageItem {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  mode: string;
  provider_used?: string | null;
  model_used?: string | null;
  citations?: any[] | null;
  diagnostics?: any | null;
  tokens_used?: number | null;
  created_at: string;
}

export interface ConversationDetail {
  id: string;
  title: string;
  subject_id?: string | null;
  system_prompt?: string | null;
  created_at: string;
  updated_at: string;
  messages: ChatMessageItem[];
}

export async function fetchConversations(params?: { q?: string; subject_id?: string }): Promise<ConversationItem[]> {
  const query = new URLSearchParams();
  if (params?.q) query.append('q', params.q);
  if (params?.subject_id) query.append('subject_id', params.subject_id);

  const res = await fetch(`${API_BASE}/conversations?${query.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch conversations');
  return res.json();
}

export async function createConversation(data?: {
  title?: string;
  subject_id?: string;
  system_prompt?: string;
}): Promise<ConversationDetail> {
  const res = await fetch(`${API_BASE}/conversations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data || {}),
  });
  if (!res.ok) throw new Error('Failed to create conversation');
  return res.json();
}

export async function fetchConversation(id: string): Promise<ConversationDetail> {
  const res = await fetch(`${API_BASE}/conversations/${id}`);
  if (!res.ok) throw new Error('Failed to fetch conversation');
  return res.json();
}

export async function updateConversation(
  id: string,
  data: { title?: string; subject_id?: string; system_prompt?: string }
): Promise<ConversationDetail> {
  const res = await fetch(`${API_BASE}/conversations/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to update conversation');
  return res.json();
}

export async function deleteConversation(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/conversations/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to delete conversation');
}

export async function exportConversationMarkdown(id: string): Promise<string> {
  const res = await fetch(`${API_BASE}/conversations/${id}/export`);
  if (!res.ok) throw new Error('Failed to export conversation');
  return res.text();
}

export function streamChat(
  params: {
    conversation_id: string;
    content: string;
    mode: string;
    subject_id?: string;
    document_ids?: string[];
    provider_id?: string;
  },
  callbacks: {
    onSources?: (chunks: any[]) => void;
    onToken?: (token: string) => void;
    onDone?: (data: any) => void;
    onError?: (error: string) => void;
  }
): () => void {
  const controller = new AbortController();

  (async () => {
    try {
      const response = await fetch(`${API_BASE}/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
        signal: controller.signal,
      });

      if (!response.ok || !response.body) {
        throw new Error(`Chat stream failed with status ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let currentEvent = 'message';
        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('event:')) {
            currentEvent = trimmed.replace('event:', '').trim();
          } else if (trimmed.startsWith('data:')) {
            const rawData = trimmed.replace('data:', '').trim();
            if (!rawData) continue;
            try {
              const parsed = JSON.parse(rawData);
              if (currentEvent === 'sources' && callbacks.onSources) {
                callbacks.onSources(parsed.chunks || []);
              } else if (currentEvent === 'token' && callbacks.onToken) {
                callbacks.onToken(parsed.content || '');
              } else if (currentEvent === 'done' && callbacks.onDone) {
                callbacks.onDone(parsed);
              } else if (currentEvent === 'error' && callbacks.onError) {
                callbacks.onError(parsed.error || 'Stream error');
              }
            } catch {
              // Non-JSON SSE line
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name !== 'AbortError' && callbacks.onError) {
        callbacks.onError(err.message || 'Stream connection error');
      }
    }
  })();

  return () => controller.abort();
}

// Memory API
export interface MemoryItem {
  id: string;
  memory_type: 'working' | 'episodic' | 'semantic' | 'profile' | 'procedural' | string;
  content: string;
  importance_score: number;
  confidence: number;
  is_pinned: boolean;
  status: string;
  source_conversation_id?: string | null;
  source_event?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuditEventItem {
  id: string;
  memory_id: string;
  action: string;
  details?: any | null;
  created_at: string;
}

export async function fetchMemories(params?: {
  memory_type?: string;
  status?: string;
  is_pinned?: boolean;
  q?: string;
}): Promise<MemoryItem[]> {
  const query = new URLSearchParams();
  if (params?.memory_type) query.append('memory_type', params.memory_type);
  if (params?.status) query.append('status', params.status);
  if (params?.is_pinned !== undefined) query.append('is_pinned', String(params.is_pinned));
  if (params?.q) query.append('q', params.q);

  const res = await fetch(`${API_BASE}/memories?${query.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch memories');
  return res.json();
}

export async function createMemory(data: {
  content: string;
  memory_type: string;
  importance_score?: number;
  confidence?: number;
  is_pinned?: boolean;
}): Promise<MemoryItem> {
  const res = await fetch(`${API_BASE}/memories`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to create memory');
  return res.json();
}

export async function updateMemory(
  id: string,
  data: Partial<MemoryItem>
): Promise<MemoryItem> {
  const res = await fetch(`${API_BASE}/memories/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to update memory');
  return res.json();
}

export async function deleteMemory(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/memories/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to delete memory');
}

export async function togglePinMemory(id: string): Promise<MemoryItem> {
  const res = await fetch(`${API_BASE}/memories/${id}/pin`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to toggle pin memory');
  return res.json();
}

export async function searchMemories(
  query: string,
  memory_types?: string[],
  top_k?: number
): Promise<{ memory: MemoryItem; similarity: number; distance: number }[]> {
  const res = await fetch(`${API_BASE}/memories/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, memory_types, top_k }),
  });
  if (!res.ok) throw new Error('Memory search failed');
  return res.json();
}

export async function extractMemoryCandidates(text: string): Promise<any[]> {
  const res = await fetch(`${API_BASE}/memories/extract-candidates`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error('Candidate extraction failed');
  return res.json();
}

export async function fetchMemoryAuditTrail(memory_id?: string): Promise<AuditEventItem[]> {
  const url = memory_id
    ? `${API_BASE}/memories/audit/trail?memory_id=${memory_id}`
    : `${API_BASE}/memories/audit/trail`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch audit trail');
  return res.json();
}

export async function exportMemories(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/memories/export`);
  if (!res.ok) throw new Error('Failed to export memories');
  return res.json();
}

export async function importMemories(items: any[]): Promise<{ imported_count: number }> {
  const res = await fetch(`${API_BASE}/memories/import`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(items),
  });
  if (!res.ok) throw new Error('Failed to import memories');
  return res.json();
}

// ==================== Academic & Learning Tools API ====================

export interface FlashcardDeckItem {
  id: string;
  name: string;
  description?: string;
  subject_id?: string;
  total_cards: number;
  due_cards: number;
  created_at: string;
}

export interface FlashcardItem {
  id: string;
  deck_id: string;
  front: string;
  back: string;
  hints?: string;
  explanation?: string;
  state: number;
  difficulty: number;
  stability: number;
  reps: number;
  lapses: number;
  scheduled_days: number;
  due_date?: string;
}

export interface FlashcardReviewResult {
  card_id: string;
  rating: number;
  new_state: number;
  stability: number;
  difficulty: number;
  scheduled_days: number;
  due_date: string;
}

export interface QuizSessionItem {
  id: string;
  title: string;
  subject_id?: string;
  difficulty: string;
  total_questions: number;
  correct_count: number;
  score_percentage: number;
  status: string;
  created_at: string;
}

export interface QuizQuestionItem {
  id: string;
  question_type: string;
  question_text: string;
  options?: string[];
  user_answer?: string;
  is_correct?: boolean;
  explanation?: string;
}

export interface QuizDetail {
  id: string;
  title: string;
  difficulty: string;
  status: string;
  total_questions: number;
  correct_count: number;
  score_percentage: number;
  questions: QuizQuestionItem[];
}

export interface QuizSubmissionResult {
  quiz_id: string;
  total_questions: number;
  correct_count: number;
  score_percentage: number;
  status: string;
  mistakes_review: {
    question_id: string;
    question_text: string;
    user_answer: string;
    correct_answer: string;
    explanation?: string;
  }[];
}

export interface CodeRunResult {
  success: boolean;
  stdout: string;
  stderr: string;
  exit_code: number;
  duration_ms: number;
  error?: string;
}

export interface DSATraceResult {
  algorithm: string;
  steps: {
    step: number;
    description: string;
    array_state: number[];
    pointers?: Record<string, number>;
  }[];
  total_steps: number;
  result: any;
}

export interface CPUScheduleResult {
  algorithm: string;
  timeline: {
    pid: string;
    start: number;
    end: number;
  }[];
  process_metrics: {
    pid: string;
    arrival: number;
    burst: number;
    completion_time: number;
    turnaround_time: number;
    waiting_time: number;
  }[];
  average_waiting_time: number;
  average_turnaround_time: number;
}

export interface BankerResult {
  is_safe: boolean;
  safe_sequence?: string[];
  error?: string;
  message?: string;
}

export interface PageReplacementResult {
  algorithm: string;
  page_faults: number;
  hits: number;
  fault_rate: number;
  steps: {
    step: number;
    page: number;
    frames: (number | null)[];
    status: 'HIT' | 'FAULT';
  }[];
}

export interface SubnetResult {
  success: boolean;
  ip_address: string;
  prefix_length: number;
  network_address: string;
  broadcast_address: string;
  netmask: string;
  wildcard_mask: string;
  usable_host_range: [string, string];
  total_hosts: number;
  usable_hosts: number;
  is_private: boolean;
}

export interface TruthTableResult {
  success: boolean;
  variables: string[];
  table: Record<string, any>[];
  total_rows: number;
}

// Flashcards API
export async function fetchFlashcardDecks(): Promise<FlashcardDeckItem[]> {
  const res = await fetch(`${API_BASE}/academic/flashcards/decks`);
  if (!res.ok) throw new Error('Failed to fetch decks');
  return res.json();
}

export async function createFlashcardDeck(data: {
  name: string;
  description?: string;
  subject_id?: string;
}): Promise<{ id: string; name: string }> {
  const res = await fetch(`${API_BASE}/academic/flashcards/decks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to create deck');
  return res.json();
}

export async function deleteFlashcardDeck(deckId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/academic/flashcards/decks/${deckId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete deck');
}

export async function fetchFlashcards(deckId: string, dueOnly = false): Promise<FlashcardItem[]> {
  const res = await fetch(`${API_BASE}/academic/flashcards/decks/${deckId}/cards?due_only=${dueOnly}`);
  if (!res.ok) throw new Error('Failed to fetch flashcards');
  return res.json();
}

export async function createFlashcard(data: {
  deck_id: string;
  front: string;
  back: string;
  hints?: string;
  explanation?: string;
}): Promise<FlashcardItem> {
  const res = await fetch(`${API_BASE}/academic/flashcards/cards`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to create flashcard');
  return res.json();
}

export async function reviewFlashcard(cardId: string, rating: number): Promise<FlashcardReviewResult> {
  const res = await fetch(`${API_BASE}/academic/flashcards/cards/${cardId}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rating }),
  });
  if (!res.ok) throw new Error('Failed to submit review');
  return res.json();
}

// Quizzes API
export async function fetchQuizzes(): Promise<QuizSessionItem[]> {
  const res = await fetch(`${API_BASE}/academic/quizzes`);
  if (!res.ok) throw new Error('Failed to fetch quizzes');
  return res.json();
}

export async function generateQuiz(data: {
  title?: string;
  subject_id?: string;
  difficulty?: string;
  question_count?: number;
  time_limit_minutes?: number;
}): Promise<{ id: string; title: string }> {
  const res = await fetch(`${API_BASE}/academic/quizzes/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to generate quiz');
  return res.json();
}

export async function fetchQuiz(quizId: string): Promise<QuizDetail> {
  const res = await fetch(`${API_BASE}/academic/quizzes/${quizId}`);
  if (!res.ok) throw new Error('Failed to fetch quiz');
  return res.json();
}

export async function submitQuiz(quizId: string, answers: Record<string, string>): Promise<QuizSubmissionResult> {
  const res = await fetch(`${API_BASE}/academic/quizzes/${quizId}/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ answers }),
  });
  if (!res.ok) throw new Error('Failed to submit quiz');
  return res.json();
}

// Math API
export async function solveMathEquation(equation: string, variable = 'x'): Promise<any> {
  const res = await fetch(`${API_BASE}/academic/math/solve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ equation, variable }),
  });
  if (!res.ok) throw new Error('Failed to solve equation');
  return res.json();
}

export async function differentiateMath(expression: string, variable = 'x', order = 1): Promise<any> {
  const res = await fetch(`${API_BASE}/academic/math/diff`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ expression, variable, order }),
  });
  if (!res.ok) throw new Error('Failed to differentiate expression');
  return res.json();
}

export async function integrateMath(
  expression: string,
  variable = 'x',
  lowerLimit?: string,
  upperLimit?: string
): Promise<any> {
  const res = await fetch(`${API_BASE}/academic/math/integrate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      expression,
      variable,
      lower_limit: lowerLimit || null,
      upper_limit: upperLimit || null,
    }),
  });
  if (!res.ok) throw new Error('Failed to integrate expression');
  return res.json();
}

export async function simplifyMath(expression: string): Promise<any> {
  const res = await fetch(`${API_BASE}/academic/math/simplify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ expression, variable: 'x' }),
  });
  if (!res.ok) throw new Error('Failed to simplify expression');
  return res.json();
}

export async function computeMatrix(matrix: number[][], operation = 'determinant'): Promise<any> {
  const res = await fetch(`${API_BASE}/academic/math/matrix`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ matrix, operation }),
  });
  if (!res.ok) throw new Error('Failed to compute matrix operation');
  return res.json();
}

// Sandbox & DSA API
export async function runSandboxCode(code: string, timeoutSeconds = 2.5): Promise<CodeRunResult> {
  const res = await fetch(`${API_BASE}/academic/sandbox/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, timeout_seconds: timeoutSeconds }),
  });
  if (!res.ok) throw new Error('Sandbox run failed');
  return res.json();
}

export async function traceAlgorithm(
  algorithm: string,
  array: number[],
  target?: number
): Promise<DSATraceResult> {
  const res = await fetch(`${API_BASE}/academic/dsa/trace`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ algorithm, array, target }),
  });
  if (!res.ok) throw new Error('DSA trace failed');
  return res.json();
}

// Simulators API
export async function simulateCPUScheduler(
  algorithm: string,
  processes: { pid: string; arrival: number; burst: number }[],
  quantum = 2
): Promise<CPUScheduleResult> {
  const res = await fetch(`${API_BASE}/academic/simulators/cpu-schedule`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ algorithm, processes, quantum }),
  });
  if (!res.ok) throw new Error('CPU schedule simulation failed');
  return res.json();
}

export async function simulateBankers(
  available: number[],
  allocation: number[][],
  maxMatrix: number[][],
  pids?: string[]
): Promise<BankerResult> {
  const res = await fetch(`${API_BASE}/academic/simulators/banker`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ available, allocation, max_matrix: maxMatrix, pids }),
  });
  if (!res.ok) throw new Error('Banker simulation failed');
  return res.json();
}

export async function simulatePageReplacement(
  algorithm: string,
  pages: number[],
  numFrames = 3
): Promise<PageReplacementResult> {
  const res = await fetch(`${API_BASE}/academic/simulators/page-replacement`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ algorithm, pages, num_frames: numFrames }),
  });
  if (!res.ok) throw new Error('Page replacement simulation failed');
  return res.json();
}

export async function calculateSubnet(ipAddress: string, prefixLength = 24): Promise<SubnetResult> {
  const res = await fetch(`${API_BASE}/academic/simulators/subnet`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ip_address: ipAddress, prefix_length: prefixLength }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Subnet calculation failed');
  }
  return res.json();
}

export async function generateTruthTable(expression: string): Promise<TruthTableResult> {
  const res = await fetch(`${API_BASE}/academic/simulators/truth-table`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ expression }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Truth table generation failed');
  }
  return res.json();
}

// ==================== Knowledge Graph & Obsidian API ====================

export interface KnowledgeNodeItem {
  id: string;
  label: string;
  node_type: string;
  description?: string;
  subject_id?: string;
  document_id?: string;
  position_x: number;
  position_y: number;
  is_verified: boolean;
  created_at?: string;
}

export interface KnowledgeEdgeItem {
  id: string;
  source_id: string;
  target_id: string;
  relationship_type: string;
  is_verified: boolean;
}

export interface GraphData {
  nodes: KnowledgeNodeItem[];
  edges: KnowledgeEdgeItem[];
}

export interface PrerequisiteChainResult {
  target: KnowledgeNodeItem;
  prerequisites_count: number;
  study_order: KnowledgeNodeItem[];
}

export interface ObsidianPreviewResult {
  vault_path: string;
  total_notes: number;
  files_to_create: string[];
  files_to_overwrite: string[];
  has_conflicts: boolean;
}

export interface ObsidianExportResult {
  vault_path: string;
  written_count: number;
  skipped_count: number;
  written_files: string[];
  skipped_files: string[];
}

export async function fetchGraph(
  subjectId?: string,
  nodeType?: string,
  verifiedOnly?: boolean
): Promise<GraphData> {
  const params = new URLSearchParams();
  if (subjectId) params.append('subject_id', subjectId);
  if (nodeType) params.append('node_type', nodeType);
  if (verifiedOnly) params.append('verified_only', 'true');

  const res = await fetch(`${API_BASE}/graph?${params.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch knowledge graph');
  return res.json();
}

export async function createGraphNode(data: {
  label: string;
  node_type?: string;
  description?: string;
  subject_id?: string;
  document_id?: string;
  position_x?: number;
  position_y?: number;
  is_verified?: boolean;
}): Promise<KnowledgeNodeItem> {
  const res = await fetch(`${API_BASE}/graph/nodes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to create node');
  return res.json();
}

export async function updateGraphNode(
  nodeId: string,
  data: Partial<KnowledgeNodeItem>
): Promise<KnowledgeNodeItem> {
  const res = await fetch(`${API_BASE}/graph/nodes/${nodeId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to update node');
  return res.json();
}

export async function deleteGraphNode(nodeId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/graph/nodes/${nodeId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete node');
}

export async function createGraphEdge(data: {
  source_id: string;
  target_id: string;
  relationship_type?: string;
  is_verified?: boolean;
}): Promise<KnowledgeEdgeItem> {
  const res = await fetch(`${API_BASE}/graph/edges`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to create edge');
  }
  return res.json();
}

export async function deleteGraphEdge(edgeId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/graph/edges/${edgeId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete edge');
}

export async function fetchPrerequisites(nodeId: string): Promise<PrerequisiteChainResult> {
  const res = await fetch(`${API_BASE}/graph/prerequisites/${nodeId}`);
  if (!res.ok) throw new Error('Failed to fetch prerequisites');
  return res.json();
}

export async function extractGraphFromDocument(documentId: string): Promise<{
  document_id: string;
  document_title: string;
  nodes_created: number;
  edges_created: number;
  concepts: string[];
}> {
  const res = await fetch(`${API_BASE}/graph/extract-from-document/${documentId}`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to extract concepts from document');
  return res.json();
}

export async function previewObsidianExport(
  vaultPath: string,
  subjectId?: string
): Promise<ObsidianPreviewResult> {
  const res = await fetch(`${API_BASE}/graph/obsidian/preview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ vault_path: vaultPath, subject_id: subjectId || null }),
  });
  if (!res.ok) throw new Error('Failed to preview Obsidian export');
  return res.json();
}

export async function exportToObsidianVault(
  vaultPath: string,
  subjectId?: string,
  allowOverwrite = false
): Promise<ObsidianExportResult> {
  const res = await fetch(`${API_BASE}/graph/obsidian/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      vault_path: vaultPath,
      subject_id: subjectId || null,
      allow_overwrite: allowOverwrite,
    }),
  });
  if (!res.ok) throw new Error('Failed to export Obsidian vault');
  return res.json();
}

export function getObsidianZipUrl(subjectId?: string): string {
  return subjectId
    ? `${API_BASE}/graph/obsidian/export-zip?subject_id=${subjectId}`
    : `${API_BASE}/graph/obsidian/export-zip`;
}




