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

