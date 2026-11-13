from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class GpuSchema(BaseModel):
    available: bool
    name: Optional[str] = None
    vram_total_mb: float = 0.0
    vram_used_mb: float = 0.0
    vram_free_mb: float = 0.0
    utilization_percent: float = 0.0
    temperature_c: Optional[float] = None
    error: Optional[str] = None


class CpuSchema(BaseModel):
    percent: float
    core_count: int
    frequency_mhz: Optional[float] = None


class RamSchema(BaseModel):
    total_mb: float
    used_mb: float
    available_mb: float
    percent: float


class DiskSchema(BaseModel):
    total_gb: float
    used_gb: float
    free_gb: float
    percent: float
    path: str


class OllamaSchema(BaseModel):
    running: bool
    version: Optional[str] = None
    installed_models: List[str] = Field(default_factory=list)
    running_models: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class SystemResourcesResponse(BaseModel):
    cpu: CpuSchema
    ram: RamSchema
    disk: DiskSchema
    gpu: GpuSchema
    ollama: OllamaSchema


class ModelFitEvaluationResponse(BaseModel):
    model_name: str
    estimated_params_b: float
    estimated_vram_needed_mb: float
    vram_available_mb: float
    fit_tier: str  # optimal, tight, exceeds_vram
    recommendation: str
    warning: Optional[str] = None
