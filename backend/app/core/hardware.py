import os
import shutil
import asyncio
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
import psutil
import httpx
from app.core.config import settings

logger = logging.getLogger("ruby.hardware")


@dataclass
class GpuMetrics:
    available: bool = False
    name: Optional[str] = None
    vram_total_mb: float = 0.0
    vram_used_mb: float = 0.0
    vram_free_mb: float = 0.0
    utilization_percent: float = 0.0
    temperature_c: Optional[float] = None
    error: Optional[str] = None


@dataclass
class CpuMetrics:
    percent: float
    core_count: int
    frequency_mhz: Optional[float] = None


@dataclass
class RamMetrics:
    total_mb: float
    used_mb: float
    available_mb: float
    percent: float


@dataclass
class DiskMetrics:
    total_gb: float
    used_gb: float
    free_gb: float
    percent: float
    path: str


@dataclass
class OllamaMetrics:
    running: bool
    version: Optional[str] = None
    installed_models: List[str] = field(default_factory=list)
    running_models: List[str] = field(default_factory=list)
    error: Optional[str] = None


class HardwareMonitor:
    """Probes host hardware and AI accelerator states with graceful fallback."""

    @staticmethod
    def get_cpu_metrics() -> CpuMetrics:
        core_count = psutil.cpu_count(logical=True) or 1
        percent = psutil.cpu_percent(interval=None)
        freq = None
        try:
            f = psutil.cpu_freq()
            if f:
                freq = round(f.current, 1)
        except Exception:
            pass
        return CpuMetrics(percent=percent, core_count=core_count, frequency_mhz=freq)

    @staticmethod
    def get_ram_metrics() -> RamMetrics:
        v = psutil.virtual_memory()
        return RamMetrics(
            total_mb=round(v.total / (1024 * 1024), 1),
            used_mb=round(v.used / (1024 * 1024), 1),
            available_mb=round(v.available / (1024 * 1024), 1),
            percent=v.percent,
        )

    @staticmethod
    def get_disk_metrics() -> DiskMetrics:
        target_dir = settings.data_dir.resolve()
        d = psutil.disk_usage(str(target_dir))
        return DiskMetrics(
            total_gb=round(d.total / (1024**3), 2),
            used_gb=round(d.used / (1024**3), 2),
            free_gb=round(d.free / (1024**3), 2),
            percent=d.percent,
            path=str(target_dir),
        )

    @staticmethod
    async def get_gpu_metrics() -> GpuMetrics:
        """Query NVIDIA GPU metrics via nvidia-smi with graceful fallback if absent."""
        nvidia_smi = shutil.which("nvidia-smi")
        if not nvidia_smi:
            return GpuMetrics(available=False, error="nvidia-smi utility not found on host.")

        cmd = [
            nvidia_smi,
            "--query-gpu=name,memory.total,memory.used,utilization.gpu,temperature.gpu",
            "--format=csv,noheader,nounits",
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=2.5)

            if proc.returncode != 0:
                err_msg = stderr.decode("utf-8", errors="ignore").strip()
                return GpuMetrics(available=False, error=f"nvidia-smi error: {err_msg}")

            line = stdout.decode("utf-8", errors="ignore").strip()
            if not line:
                return GpuMetrics(available=False, error="No GPU detected in nvidia-smi output.")

            # Example: "NVIDIA GeForce RTX 3050 6GB Laptop GPU, 6144, 42, 0, 40.81"
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 4:
                name = parts[0]
                total = float(parts[1])
                used = float(parts[2])
                util = float(parts[3])
                temp = float(parts[4]) if len(parts) >= 5 else None

                return GpuMetrics(
                    available=True,
                    name=name,
                    vram_total_mb=total,
                    vram_used_mb=used,
                    vram_free_mb=max(0.0, total - used),
                    utilization_percent=util,
                    temperature_c=temp,
                )
            return GpuMetrics(available=False, error="Unexpected nvidia-smi format.")
        except asyncio.TimeoutError:
            return GpuMetrics(available=False, error="nvidia-smi query timed out.")
        except Exception as e:
            return GpuMetrics(available=False, error=str(e))

    @staticmethod
    async def get_ollama_metrics() -> OllamaMetrics:
        """Probe local Ollama daemon for status, installed models, and loaded models."""
        base_url = settings.ollama_base_url.rstrip("/")
        tags_url = f"{base_url}/api/tags"
        ps_url = f"{base_url}/api/ps"
        version_url = f"{base_url}/api/version"

        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res_tags = await client.get(tags_url)
                if res_tags.status_code != 200:
                    return OllamaMetrics(
                        running=False,
                        error=f"Ollama returned HTTP {res_tags.status_code}",
                    )

                installed = [m.get("name", "") for m in res_tags.json().get("models", [])]

                # Check version
                version = None
                try:
                    res_ver = await client.get(version_url)
                    if res_ver.status_code == 200:
                        version = res_ver.json().get("version")
                except Exception:
                    pass

                # Check currently loaded models
                running_models = []
                try:
                    res_ps = await client.get(ps_url)
                    if res_ps.status_code == 200:
                        running_models = [m.get("name", "") for m in res_ps.json().get("models", [])]
                except Exception:
                    pass

                return OllamaMetrics(
                    running=True,
                    version=version,
                    installed_models=installed,
                    running_models=running_models,
                )
        except Exception as e:
            return OllamaMetrics(
                running=False,
                error=f"Ollama unreachable at {base_url}: {str(e)}",
            )

    @classmethod
    def evaluate_model_fit(
        cls,
        model_name: str,
        vram_available_mb: float = 6144.0,
        parameter_size_b: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate if a model fits in GPU VRAM (specifically calibrated for RTX 3050 6GB).
        Rule of thumb for 4-bit quant: ~0.6 GB per billion parameters + ~1.5 GB for KV cache/context.
        """
        name_lower = model_name.lower()

        # Deduce parameter size if not supplied
        if parameter_size_b is None:
            if "70b" in name_lower:
                parameter_size_b = 70.0
            elif "32b" in name_lower:
                parameter_size_b = 32.0
            elif "14b" in name_lower:
                parameter_size_b = 14.0
            elif "8b" in name_lower or ":8b" in name_lower:
                parameter_size_b = 8.0
            elif "7b" in name_lower or ":7b" in name_lower:
                parameter_size_b = 7.0
            elif "3b" in name_lower or "3.2" in name_lower or ":3b" in name_lower:
                parameter_size_b = 3.2
            elif "1b" in name_lower or ":1b" in name_lower:
                parameter_size_b = 1.0
            else:
                parameter_size_b = 7.0  # default assumption

        # Q4_K_M quantized model: ~550 MB per billion params + ~800 MB KV cache (4k context)
        estimated_vram_mb = (parameter_size_b * 550.0) + 800.0

        if estimated_vram_mb <= (vram_available_mb * 0.70):
            fit_tier = "optimal"
            recommendation = "Fits comfortably in VRAM. Recommended for fast local academic tutoring and chat."
            warning = None
        elif estimated_vram_mb <= (vram_available_mb * 0.95):
            fit_tier = "tight"
            recommendation = "Fits in VRAM with moderate context window (up to 8,192 tokens). Monitor VRAM utilization."
            warning = "Avoid loading multiple models concurrently."
        else:
            fit_tier = "exceeds_vram"
            recommendation = (
                f"Model size (~{round(parameter_size_b, 1)}B) exceeds available 6GB VRAM. "
                "Will trigger heavy CPU offloading, resulting in significantly higher latency. "
                "Consider using a 3B or 7B-8B 4-bit quantized model instead."
            )
            warning = "High risk of out-of-memory or steep inference slowdown."

        return {
            "model_name": model_name,
            "estimated_params_b": parameter_size_b,
            "estimated_vram_needed_mb": round(estimated_vram_mb, 1),
            "vram_available_mb": vram_available_mb,
            "fit_tier": fit_tier,
            "recommendation": recommendation,
            "warning": warning,
        }


hardware_monitor = HardwareMonitor()
