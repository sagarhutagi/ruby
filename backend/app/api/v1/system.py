from typing import Optional
from fastapi import APIRouter, Query
from app.core.hardware import hardware_monitor
from app.schemas.system import (
    SystemResourcesResponse,
    CpuSchema,
    RamSchema,
    DiskSchema,
    GpuSchema,
    OllamaSchema,
    ModelFitEvaluationResponse,
)

router = APIRouter(prefix="/system", tags=["System & Hardware Diagnostics"])


@router.get("/resources", response_model=SystemResourcesResponse, summary="Live Hardware Telemetry")
async def get_system_resources() -> SystemResourcesResponse:
    cpu = hardware_monitor.get_cpu_metrics()
    ram = hardware_monitor.get_ram_metrics()
    disk = hardware_monitor.get_disk_metrics()
    gpu = await hardware_monitor.get_gpu_metrics()
    ollama = await hardware_monitor.get_ollama_metrics()

    return SystemResourcesResponse(
        cpu=CpuSchema(
            percent=cpu.percent,
            core_count=cpu.core_count,
            frequency_mhz=cpu.frequency_mhz,
        ),
        ram=RamSchema(
            total_mb=ram.total_mb,
            used_mb=ram.used_mb,
            available_mb=ram.available_mb,
            percent=ram.percent,
        ),
        disk=DiskSchema(
            total_gb=disk.total_gb,
            used_gb=disk.used_gb,
            free_gb=disk.free_gb,
            percent=disk.percent,
            path=disk.path,
        ),
        gpu=GpuSchema(
            available=gpu.available,
            name=gpu.name,
            vram_total_mb=gpu.vram_total_mb,
            vram_used_mb=gpu.vram_used_mb,
            vram_free_mb=gpu.vram_free_mb,
            utilization_percent=gpu.utilization_percent,
            temperature_c=gpu.temperature_c,
            error=gpu.error,
        ),
        ollama=OllamaSchema(
            running=ollama.running,
            version=ollama.version,
            installed_models=ollama.installed_models,
            running_models=ollama.running_models,
            error=ollama.error,
        ),
    )


@router.get("/model-check", response_model=ModelFitEvaluationResponse, summary="Hardware-Aware Model Memory Fit")
async def check_model_fit(
    model: str = Query(..., description="Model name or identifier (e.g. llama3.2:3b, qwen2.5:7b, llama3.3:70b)"),
    params_b: Optional[float] = Query(None, description="Optional parameter size in billions"),
) -> ModelFitEvaluationResponse:
    gpu = await hardware_monitor.get_gpu_metrics()
    vram_mb = gpu.vram_total_mb if gpu.available and gpu.vram_total_mb > 0 else 6144.0

    eval_result = hardware_monitor.evaluate_model_fit(
        model_name=model,
        vram_available_mb=vram_mb,
        parameter_size_b=params_b,
    )
    return ModelFitEvaluationResponse(**eval_result)
