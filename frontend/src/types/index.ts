export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'offline';
  app_name: string;
  version: string;
  environment: string;
  database_connected: boolean;
  storage_accessible: boolean;
  data_directory: string;
  timestamp: string;
}

export interface SubjectItem {
  id: string;
  name: string;
  description?: string;
  color: string;
  icon?: string;
  created_at: string;
}

export interface SystemResourceMetrics {
  cpu_percent: number;
  memory_used_mb: number;
  memory_total_mb: number;
  memory_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
  disk_percent: number;
  gpu_available: boolean;
  gpu_name?: string;
  gpu_vram_used_mb?: number;
  gpu_vram_total_mb?: number;
  gpu_utilization_percent?: number;
  ollama_status: 'running' | 'unreachable' | 'disabled';
  loaded_models: string[];
}
