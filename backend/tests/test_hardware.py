import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.hardware import HardwareMonitor, GpuMetrics


def test_cpu_ram_disk_metrics():
    cpu = HardwareMonitor.get_cpu_metrics()
    assert cpu.core_count >= 1
    assert 0.0 <= cpu.percent <= 100.0

    ram = HardwareMonitor.get_ram_metrics()
    assert ram.total_mb > 1000
    assert ram.used_mb > 0
    assert 0.0 <= ram.percent <= 100.0

    disk = HardwareMonitor.get_disk_metrics()
    assert disk.total_gb > 1.0
    assert 0.0 <= disk.percent <= 100.0


@pytest.mark.asyncio
async def test_gpu_metrics_graceful_fallback():
    # Simulate host without nvidia-smi
    with patch("shutil.which", return_value=None):
        metrics = await HardwareMonitor.get_gpu_metrics()
        assert metrics.available is False
        assert "not found" in metrics.error


@pytest.mark.asyncio
async def test_gpu_metrics_mocked_success():
    # Simulate valid nvidia-smi output
    mock_stdout = b"NVIDIA GeForce RTX 3050 6GB Laptop GPU, 6144, 1024, 15, 45\n"
    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate.return_value = (mock_stdout, b"")

    with patch("shutil.which", return_value="/usr/bin/nvidia-smi"):
        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            metrics = await HardwareMonitor.get_gpu_metrics()
            assert metrics.available is True
            assert metrics.name == "NVIDIA GeForce RTX 3050 6GB Laptop GPU"
            assert metrics.vram_total_mb == 6144.0
            assert metrics.vram_used_mb == 1024.0
            assert metrics.vram_free_mb == 5120.0
            assert metrics.utilization_percent == 15.0
            assert metrics.temperature_c == 45.0


def test_model_fit_evaluation():
    # 3B model (e.g. llama3.2:3b) on 6GB VRAM
    fit_3b = HardwareMonitor.evaluate_model_fit("llama3.2:3b", vram_available_mb=6144.0)
    assert fit_3b["fit_tier"] == "optimal"
    assert fit_3b["warning"] is None

    # 8B model (e.g. llama3:8b) on 6GB VRAM
    fit_8b = HardwareMonitor.evaluate_model_fit("llama3:8b", vram_available_mb=6144.0)
    assert fit_8b["fit_tier"] in ["tight", "optimal"]

    # 70B model on 6GB VRAM
    fit_70b = HardwareMonitor.evaluate_model_fit("llama3.3:70b", vram_available_mb=6144.0)
    assert fit_70b["fit_tier"] == "exceeds_vram"
    assert "exceeds" in fit_70b["recommendation"].lower()
    assert fit_70b["warning"] is not None


@pytest.mark.asyncio
async def test_system_api_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Live hardware resources
        res = await client.get("/api/v1/system/resources")
        assert res.status_code == 200
        data = res.json()
        assert "cpu" in data
        assert "ram" in data
        assert "disk" in data
        assert "gpu" in data
        assert "ollama" in data
        assert data["cpu"]["core_count"] >= 1
        assert data["ram"]["total_mb"] > 0

        # Model check endpoint
        model_res = await client.get("/api/v1/system/model-check?model=llama3.2:3b")
        assert model_res.status_code == 200
        check_data = model_res.json()
        assert check_data["fit_tier"] == "optimal"
        assert check_data["estimated_params_b"] == 3.2
