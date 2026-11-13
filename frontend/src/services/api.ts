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
